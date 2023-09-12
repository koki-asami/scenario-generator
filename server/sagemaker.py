# sagemaker endpoint
import base64
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from logging import getLogger
from logging.config import dictConfig

import torch
from flask import Blueprint, jsonify, make_response, request

from domain.predict_domain import AlgorithmPredictRequest
from exceptions import InvalidParameterError, NotFound
from services.predict_service import AlgorithmPredictService

# from auth import is_authorized

dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'develop': {
            'format': '%(asctime)s [%(levelname)s] %(pathname)s:%(lineno)d '
                      '%(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'develop',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'matplotlib': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'urllib3': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    },
})

logger = getLogger(__name__)

logger.warning(f'torch.cuda.is_available(): {torch.cuda.is_available()}')

# thread pool for upload and download
thread_pool = ThreadPoolExecutor(max_workers=os.environ.get('NUM_HTTP_PARALLEL', 40))

sagemaker_apis = Blueprint('sagemaker_apis', __name__)


@sagemaker_apis.route('/ping', methods=['GET'])
def ping():
    health = True
    status = 200 if health else 404
    return make_response(jsonify('\n'), status)


@sagemaker_apis.route('/invocations', methods=['POST'])
def invocations():
    # if not is_authorized():
    #     return jsonify({'error': 'Unauthorized.'}), 401
    try:
        if request.is_json:
            # ACES Platform v1.1からrequestはformで統一されてjsonでこない
            logger.info(request.json)
            message = AlgorithmPredictRequest.from_dict(request.json)
        else:
            logger.info(request.form)
            message = AlgorithmPredictRequest.from_json(request.form['message'])
        if message.callback_url:
            # sagemaker async
            results, metrics, file, mime = AlgorithmPredictService().predict(message)
        else:
            # sagemaker sync
            timeout_at = datetime.now() + timedelta(seconds=50)  # TODO: not set if async.
            results, metrics, file, mime = AlgorithmPredictService().predict(message, files=request.files, timeout_at=timeout_at, pool=thread_pool)  # NOQA
        if file:
            response = {
                'file': base64.b64encode(file),
                'metrics': metrics,
                'mime': mime,
            }
        else:
            response = {
                'results': results,
                'metrics': metrics,
                'mime': mime,
            }
        return jsonify(response)
    except NotFound as e:
        return make_response(jsonify(str(e)), 404)
    except InvalidParameterError as e:
        return make_response(jsonify(str(e)), 400)
    except Exception as e:
        logger.error(str(e), exc_info=True)
        return make_response(jsonify(str(e)), 500)
