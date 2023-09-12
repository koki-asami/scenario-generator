import os
import sys
import tempfile
import traceback
import unittest

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
from domain.predict_domain import AlgorithmPredictRequest  # NOQA
from services.predict_service import AlgorithmPredictService  # NOQA


class TestAlgorithmPredictService(unittest.TestCase):
    def test_predict_service_type_file(self):
        """test predict_service type_file."""
        try:
            test_json_input = open('algorithms/algorithm.json', mode='rb')
            test_zip_input = open('algorithms/example_algorithm.png', mode='rb')  # どのファイルでも良い
            test_json_output = tempfile.NamedTemporaryFile(delete=True, suffix='.json')
            test_zip_output = tempfile.NamedTemporaryFile(delete=True, suffix='.zip')
            service = AlgorithmPredictService()
            dict = {
                'request_id': '1',
                'task_name': 'example_file_algorithm',
                'algorithm_type': 'file',
                'data': [
                    {
                        'url': f'file://{test_json_input.name}',
                        'content_type': 'application/json',
                    },
                    {
                        'url': f'file://{test_zip_input.name}',
                        'content_type': 'application/zip',
                    },
                ],
                'results_files_upload_url': [
                    {
                        'url': f'file://{test_json_output.name}',
                        'content_type': 'application/json',
                    },
                    {
                        'url': f'file://{test_zip_output.name}',
                        'content_type': 'application/zip',
                    },
                ],
                'options': {},
            }
            message = AlgorithmPredictRequest(**dict)
            service.predict(message)
            self.assertEqual(test_json_input.read(), test_json_output.read())
            self.assertEqual(test_zip_input.read(), test_zip_output.read())
        except RuntimeError:
            self.fail(traceback.format_exc())


if __name__ == '__main__':
    unittest.main()
