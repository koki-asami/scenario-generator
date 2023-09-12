import io
import logging
from typing import Any, BinaryIO, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MockAlgorithm():
    """Mock ALgorithm
    これは説明用のサンプルでAPI提供時はこのMockは削除し、AEが作成したアルゴリズムモジュールをimportして呼び出す
    """
    def __init__(self, **params):
        pass

    def __call__(self, files: List[BinaryIO], **kwargs) -> Tuple[List[BinaryIO], List[List[Any]]]:
        logger.info(f'{np.shape(files)} {kwargs=}')
        input_files = []
        for file in files:
            input_files.append(file.read())
        [logger.info(file[:100]) for file in input_files]
        output_files = []
        for file in input_files:
            buf = io.BytesIO(file)
            buf.seek(0)
            output_files.append(buf)
        # logger.debug([file.read() for file in output_files])
        metrics = [
                    ['number_of_vertical_rebars', 50],
                    ['number_of_horizontal_rebars', 120],
                    ['number_of_markers', 10],
                    ['average_rebar_diameter', 30],
                    ['average_rebar_spacing', 250],
                  ]
        return output_files, metrics


class ExampleAlgorithmFacade():
    """サーバからAlgorithmを呼び出すFacadeクラス
    algorithm_type=FILEの場合、アルゴリズムの初期化を行う__init__()、推論実行時にアルゴリズムを呼び出す__call__()の実装が必要
    __call__()では引数としてファイルリストが渡され、レスポンスはファイルリストで返す。
    """
    def __init__(self, num_workers=0, batch_size=None, **params):
        params['TEST'] = {'NUM_WORKER': num_workers}
        if batch_size:
            params['TEST']['BATCH_SIZE'] = batch_size
        self.model = MockAlgorithm(**params)

    def __call__(self, files: List[BinaryIO], **kwargs) -> Tuple[List[BinaryIO], List[List[Any]], int]:
        results, metrics = self.model(files, **kwargs)
        # 課金カウント: 画像/動画の場合はフレーム数など, 音声の場合推論秒数等のプロジェクトで決めた課金単位を計算してセット
        inference_count = len(results)
        return results, metrics, inference_count
