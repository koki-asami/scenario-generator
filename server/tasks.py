# aws batch endpoint
import logging
import os
import sys
from logging import INFO, Formatter, StreamHandler, getLogger

from aws_xray_sdk.core import patch, xray_recorder

from domain.predict_domain import AlgorithmPredictRequest
from services.predict_service import AlgorithmPredictService

Project = os.environ.get('Project')
logger = getLogger(__name__)
sh = StreamHandler()
sh.setFormatter(Formatter('[%(levelname)s] %(asctime)s %(message)s'))
logger.addHandler(sh)
logger.setLevel(INFO)
patch(['boto3', 'requests'])
xray_recorder.configure(service=f'{Project}-batch', plugins=('ECSPlugin',),
                        context_missing='LOG_ERROR')
logging.getLogger('aws_xray_sdk').setLevel(logging.FATAL)


def main() -> None:
    if len(sys.argv) != 2:
        logger.warning('******** Usage : message(e.g. {"task_name": "object_detection", ... }) ********')
        raise Exception('Arguments are incorrect. %s' % (sys.argv))
    logger.info(sys.argv[1])
    xray_recorder.begin_segment()
    if xray_recorder.is_sampled():
        xray_recorder.put_annotation('message', sys.argv[1])

    try:
        message = AlgorithmPredictRequest.from_json(sys.argv[1])
        AlgorithmPredictService().predict(message)
    finally:
        xray_recorder.end_segment()


if __name__ == '__main__':
    main()
