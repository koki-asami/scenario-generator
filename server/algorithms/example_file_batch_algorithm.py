import logging
from typing import Any, BinaryIO, List, Tuple

from algorithms.example_file_algorithm import MockAlgorithm

logger = logging.getLogger(__name__)


class ExampleAlgorithmFacade():
    """aws batch動作確認用
    """
    def __init__(self, **params):
        self.model = MockAlgorithm(**params)

    def __call__(self, files: List[BinaryIO], **kwargs) -> Tuple[List[BinaryIO], List[List[Any]], int]:
        results, metrics = self.model(files, **kwargs)
        inference_count = len(results)
        return results, metrics, inference_count
