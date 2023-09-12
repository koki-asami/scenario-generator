import logging
from typing import Any, List, Optional, Tuple

import numpy as np

# from acesvision.ObjectDetection import CenterNet

# CONF_THRE = os.environ.get('CONF_THRE', 0.2)
logger = logging.getLogger(__name__)


class MockAlgorithm():
    """Mock ALgorithm
    これは説明用のサンプルでAPI提供時はこのMockは削除し、AEが作成したアルゴリズムモジュールをimportして呼び出す
    """
    def __init__(self, **params):
        pass

    def __call__(self, images: List[np.ndarray], **kwargs) -> Tuple[List[List[dict]], List[List[Any]], int]:
        logger.info(f'{type(images)} {np.shape(images)} {kwargs=}')
        results = [[{
                    'bbox': {
                        'h': 21.871295928955078,
                        'w': 26.435710906982422,
                        'x': 166.0182647705078,
                        'y': 10.05595874786377,
                    },
                    'class': 2,
                    'confidence': 0.9843447804450989,
                    'label': 'car',
                    }]]
        metrics = [
                    ['number_of_vertical_rebars', 50],
                    ['number_of_horizontal_rebars', 120],
                    ['number_of_markers', 10],
                    ['average_rebar_diameter', 30],
                    ['average_rebar_spacing', 250],
                  ]
        return results, metrics

    def draw(self, image: np.ndarray, result: List[dict], **draw_args) -> np.ndarray:
        logger.info(type(image))
        return image


class ExampleAlgorithmFacade():
    """サーバからAlgorithmを呼び出すFacadeクラス
    algorithm_type=SIMPLEの場合、アルゴリズムの初期化を行う__init__()、推論実行時にアルゴリズムを呼び出す__call__()、
    ACES Platform UIで表示する描画済データ生成のために呼び出されるdraw()の実装が必要
    __call__()は引数としてサーバから画像リストが渡されるが、draw()は画像1枚毎に呼び出されるので注意
    """
    def __init__(self, num_workers=0, batch_size=None, **params):
        params['TEST'] = {'NUM_WORKER': num_workers}
        if batch_size:
            params['TEST']['BATCH_SIZE'] = batch_size
        # self.model = CenterNet(**params)
        self.model = MockAlgorithm(**params)

    def __call__(self, images: List[np.ndarray], **kwargs) -> Tuple[List[List[dict]], List[List[Any]], Optional[int]]:
        model_kwargs = {}
        # model_kwargs = {'conf_thre': kwargs.get('conf_thre', CONF_THRE)}
        results, metrics = self.model(images, return_name=True, **model_kwargs)
        # 課金カウント: 画像/動画の場合はフレーム数など, 音声の場合推論秒数等のプロジェクトで決めた課金単位を計算してセット
        inference_count = len(results)
        return results, metrics, inference_count

    def draw(self, image: np.ndarray, result: List[dict], **draw_args) -> np.ndarray:
        """Visualize inference results.
        https://github.com/aces-inc/aces-algorithm-base/blob/develop/notebook/acesvision_inference.ipynb
        example usage (from caller):
        ```
        results = example_algorithm(images)
        result_image = example_algorithm.draw(images[0], results[0])
        plt.imshow(result_image)
        ```

        Args:
            image (numpy.ndarray): An array of an original image.
                dtype = numpy.uint8
                shape = (height, width, 3)
            result (List[dict]): An element of a return value of an algorithm.
            kwargs (*): Keyword arguments for __call__ method of the drawer.
        Returns:
            image (numpy.ndarray): An array of the image with the result information.
                dtype = numpy.uint8
                shape = (height, width, 3)
        """
        return self.model.draw(image, result, **draw_args)
