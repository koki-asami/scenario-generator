import copy
import io
import json
import logging
import os
import tarfile
import tempfile
from typing import BinaryIO, Tuple

import numpy as np
import requests
import torch

from domain.predict_domain import TYPE_FILE, TYPE_IMAGE, TYPE_SIMPLE, AlgorithmPredictCallback, AlgorithmPredictRequest
from exceptions import InvalidParameterError, NotFound
from profiling import MemProfiler, TimeProfiler
from profiling.gpu_info import Trace
from services.aws import send_metrics_to_sns, send_request_log_to_sns
from services.content_handler import LocalFileAdapter, create_handler, frame_to_file
from services.utils import JPEG, JSON, NestedDictWriter, generate_fieldnames

# from vidgear.gears import WriteGear


DATA_PATH = os.environ.get('DATA_PATH', None)
MODEL_HASH = os.environ.get('MODEL_HASH', None)
WEIGHT_EXTRACT_DATA_PATH = os.environ.get('WEIGHT_EXTRACT_DATA_PATH', '/opt/ml/model')
REQUEST_TIMEOUT = 5
UPLOAD_RESULT_TIMEOUT = 120
Project = os.environ.get('Project')
logger = logging.getLogger(__name__)

predictors = {}
model_args = {}
predictor_apis = {}
model_construct_params = {}
draw_args = {}

if DATA_PATH:
    model_construct_params['data_root'] = DATA_PATH
    try:
        if not os.path.exists(DATA_PATH):
            # AWS Batch
            import boto3

            S3_WEIGHT_FILE_BUCKET = os.environ.get('S3_WEIGHT_FILE_BUCKET')
            S3_WEIGHT_FILE_PATH = os.environ.get('S3_WEIGHT_FILE_PATH')
            s3 = boto3.resource('s3')
            s3_bucket = s3.Bucket(S3_WEIGHT_FILE_BUCKET)
            with tempfile.NamedTemporaryFile(suffix='.tar.gz') as s3_weight_file:
                s3_bucket.download_file(S3_WEIGHT_FILE_PATH, s3_weight_file.name)
                with tarfile.open(s3_weight_file.name, 'r:gz') as tar:
                    os.makedirs(WEIGHT_EXTRACT_DATA_PATH, exist_ok=True)
                    tar.extractall(WEIGHT_EXTRACT_DATA_PATH)
    finally:
        for path, subdirs, files in os.walk(WEIGHT_EXTRACT_DATA_PATH):
            for name in files[:100]:
                logger.info(os.path.join(path, name))

if MODEL_HASH:
    model_construct_params['model_hash'] = MODEL_HASH

with open('algorithms/algorithm.json') as f:
    algorithms = json.load(f)

for snake_task_name, info in algorithms.items():
    algorithm_module = __import__(f'algorithms.{info["task_name"]}', fromlist=[info['class']])

    if 'det_model' in info.keys():
        det_module = __import__(f'algorithms.{info["det_model"]["task_name"]}', fromlist=[info['det_model']['class']])
        det_model = getattr(det_module, info['det_model']['class'])(
            model_hash=info['det_model']['model_hash'],
            **model_construct_params,
        )
        pred_module = __import__(
            f'algorithms.{info["pred_model"]["task_name"]}',
            fromlist=[info['pred_model']['class']],
        )
        pred_model = getattr(pred_module, info['pred_model']['class'])(
            model_hash=info['pred_model']['model_hash'],
            **model_construct_params,
        )
        api_cls = getattr(algorithm_module, info['class'])

        params = {
            'det_model': det_model,
            'pred_model': pred_model,
        }
        if 'fan_model' in info.keys():
            fan_info = info['fan_model']
            fan_module = __import__(f"algorithms.{fan_info['task_name']}", fromlist=[fan_info['class']])
            fan_model = getattr(fan_module, fan_info['class'])(
                model_hash=fan_info['model_hash'],
                **model_construct_params,
            )
            params['fan_model'] = fan_model
        if 'hpe_model' in info.keys():
            hpe_info = info['hpe_model']
            hpe_module = __import__(f"algorithms.{hpe_info['task_name']}", fromlist=[hpe_info['class']])
            hpe_model = getattr(hpe_module, hpe_info['class'])(**model_construct_params)
            params['hpe_model'] = hpe_model

        # predictors[snake_task_name] = api_cls(det_model=det_model, pred_model=pred_model)
        predictors[snake_task_name] = api_cls(**params)
    else:
        if 'model_hash' in info.keys():
            predictors[snake_task_name] = getattr(algorithm_module, info['class'])(
                model_hash=info['model_hash'],
                **model_construct_params,
            )
        else:
            predictors[snake_task_name] = getattr(algorithm_module, info['class'])(**model_construct_params)

    model_args[snake_task_name] = info.get('model_args', {})
    draw_args[snake_task_name] = info.get('draw', {}).get('args', {})


def save_json(upload_url, results, timeout=REQUEST_TIMEOUT) -> None:
    res = requests.put(upload_url, bytearray(json.dumps(results), encoding='utf-8'), timeout=timeout)
    res.raise_for_status()


def save_csv(upload_url, results, timeout=REQUEST_TIMEOUT) -> None:
    csv_fieldnames = ['id'] + generate_fieldnames(results[0])
    csv_file = io.StringIO()
    csv_writer = NestedDictWriter(csv_file, csv_fieldnames, raise_on_missing=False)
    csv_writer.writeheader()
    csv_writer.writerows(results, first_id=0)
    csv_file.seek(0)
    res = requests.put(upload_url, bytearray(csv_file.read(), encoding='utf-8'), timeout=timeout)
    res.raise_for_status()


def save_file(upload_url, file: BinaryIO, timeout=UPLOAD_RESULT_TIMEOUT) -> None:
    requests_session = requests.session()
    requests_session.mount('file://', LocalFileAdapter())
    res = requests_session.put(upload_url, data=file, timeout=timeout)
    logger.info(res.text)
    res.raise_for_status()


class AlgorithmPredictService:
    _mem_profiler = None

    def __init__(self) -> None:
        logger.warning(f'torch.cuda.is_available(): {torch.cuda.is_available()}')
        self.__class__._mem_profiler = MemProfiler() if os.environ.get('MEM_PROFILE') else None
        self.trace = Trace(os.environ.get('GPU_PROFILE', False))

    def _validate(self, message: AlgorithmPredictRequest) -> None:
        if message.algorithm_type not in [TYPE_SIMPLE, TYPE_IMAGE, TYPE_FILE]:
            raise InvalidParameterError(f'invalid {message.algorithm_type=}')
        if message.algorithm_type == TYPE_FILE:
            if message.results_to_show:
                raise InvalidParameterError(f'{message.algorithm_type=} not supports results_to_show')
        if len(message.data) > 1:
            if message.algorithm_type == TYPE_IMAGE:
                raise InvalidParameterError(f'{message.algorithm_type=} not supports multi files.')
            if message.algorithm_type == TYPE_SIMPLE and message.data[0].content_type.startswith('video/'):
                raise InvalidParameterError(f'{message.algorithm_type=} video not supports multi files.')
        if message.task_name not in predictors:
            raise NotFound('algorithm is not found')

    def predict(
        self,
        message: AlgorithmPredictRequest,
        files: dict = None,
        timeout_at=None,
        pool=None,
    ) -> Tuple[list, BinaryIO, str]:
        ticker = TimeProfiler() if os.environ.get('TIME_PROFILE') else None
        ticker and ticker.start()
        self.__class__._mem_profiler and self.__class__._mem_profiler.start()

        # validate domain data
        self._validate(message)

        try:
            model = predictors[message.task_name]
            handler = create_handler(message, timeout_at=timeout_at, pool=pool)

            ticker and ticker.tic('start download')
            frame_or_files, fps = handler.download_frame_or_files(files=files)
            logger.info(f'frame_or_files={np.shape(frame_or_files)}')
            count = len(frame_or_files)

            params = copy.deepcopy(model_args[message.task_name])
            if message.params:
                params.update(message.params)
            if fps:
                params['fps'] = fps  # TODO: handling if set or not.

            ticker and ticker.tic('start predict')
            with self.trace.timer('predict'):
                model_return_val = model(frame_or_files, **params)
            if type(model_return_val) is not tuple:
                results = model_return_val
                metrics = None
                # 課金カウント: 画像/動画の場合はフレーム数など, 音声の場合推論秒数等のプロジェクトで決めた課金単位を計算してセット。指定がない場合はリクエスト数を1として計算
                count = 1
            elif len(model_return_val) == 2:
                results = model_return_val[0]
                metrics = model_return_val[1]
                # 課金カウント: 画像/動画の場合はフレーム数など, 音声の場合推論秒数等のプロジェクトで決めた課金単位を計算してセット。指定がない場合はリクエスト数を1として計算
                count = 1
            elif len(model_return_val) > 2:
                results = model_return_val[0]
                metrics = model_return_val[1]
                count = model_return_val[2]
            logger.info(f'results={np.shape(results)}')
            assert type(results) is list, 'algorithm call() response must be list'
            ticker and ticker.tic('finish predict')

            ticker and ticker.tic('start draw and upload')
            file, output_mime = None, None
            if message.data[0].results_json_upload_url:
                save_json(message.data[0].results_json_upload_url, results, timeout=timeout_at)
            if message.data[0].results_csv_upload_url:
                save_csv(message.data[0].results_csv_upload_url, results, timeout=timeout_at)
            if message.algorithm_type == TYPE_IMAGE:
                # deprecated: use TYPE_FILE.
                if str(message.data[0].content_type).startswith('video/'):
                    raise NotImplementedError('algorithm_type:image video not supported.')
                else:
                    frames = [
                        predictors[message.task_name].draw(
                            frame_or_files[0],
                            results[0],
                            **draw_args[message.task_name],
                        ),
                    ]
                    if message.data[0].results_to_show:
                        handler.upload_frames(frames[0])
                    file = frame_to_file(frames)
                    output_mime = JPEG
            elif message.algorithm_type == TYPE_SIMPLE:
                if message.results_to_show:
                    result_images = []
                    for frame, result in zip(frame_or_files, results):
                        image = predictors[message.task_name].draw(frame, result, **draw_args[message.task_name])
                        assert type(image) is np.ndarray, 'algorithm draw() response must be image ndarray'
                        result_images.append(image)
                    # both video/image will be uploaded.
                    handler.upload_frames(result_images)
            elif message.algorithm_type == TYPE_FILE:
                if message.results_to_show:
                    raise InvalidParameterError(f'{message.algorithm_type=} not supports results_to_show')
                if not message.output_mimes:
                    output_mime = JSON
                else:
                    output_mime = message.output_mimes[0]
                # upload results_files
                for results_files_upload_url, result in zip(message.results_files_upload_url, results):
                    save_file(results_files_upload_url.url, result, timeout=timeout_at)
                    result.seek(0)
                if output_mime == JSON:
                    results = json.loads(results[0].read())
                else:
                    file = results[0]

            ticker and ticker.tic('finish draw and upload')
            data = AlgorithmPredictCallback(
                message.request_id,
                True,
                message.task_name,
                count,
                None,
                metrics,
                message.tenant_uuid,
            )
            # 同期APIでもpredict_service側からは利用ログを記録できないので、非同期API同様SNS通知にてログを送信する
            send_request_log_to_sns(data)
            if message.callback_url:
                send_metrics_to_sns(data)
            return results, metrics, file, output_mime

        except Exception as e:
            logger.error(e, exc_info=True)
            data = AlgorithmPredictCallback(
                message.request_id,
                False,
                message.task_name,
                None,
                None,
                None,
                message.tenant_uuid,
            )
            # 同期APIでもpredict_service側からは利用ログを記録できないので、非同期API同様SNS通知にてログを送信する
            send_request_log_to_sns(data)
            if message.callback_url:
                send_metrics_to_sns(data)
            raise e

        finally:
            if self.__class__._mem_profiler:
                self.__class__._mem_profiler.finish()
                self.__class__._mem_profiler.output()
            if ticker:
                ticker.finish()
