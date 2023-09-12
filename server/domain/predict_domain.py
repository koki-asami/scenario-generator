from dataclasses import field
from typing import Any, List, Optional

from dataclasses_json import LetterCase, config, dataclass_json
from pydantic.dataclasses import dataclass

#
# algorithm type
#

# simple : 画像 1 枚、または複数枚(または動画を複数枚に分割)、から JSON を出力
TYPE_SIMPLE = 'simple'
# image : (deprecated: use file) 画像 1 枚から 1 枚の画像を出力
TYPE_IMAGE = 'image'
# file : アルゴリズムにファイルを渡して推論 (出力はアルゴリズム個別のmime設定で出力)
TYPE_FILE = 'file'

ALGORITHM_TYPE_ALL = [TYPE_SIMPLE, TYPE_IMAGE, TYPE_FILE]

#
# state enum
#

UPLOADING = 'uploading'
PROCESSING = 'processing'
SUCCESS = 'success'
PARTIAL = 'partial'
ERROR = 'error'
ALL = [UPLOADING, PROCESSING, SUCCESS, PARTIAL, ERROR]


@dataclass_json
@dataclass
class ProviderURLField:
    url: str
    content_type: str = field(metadata=config(letter_case=LetterCase.KEBAB))


@dataclass_json
@dataclass
class UploadDataField:
    url: str
    content_type: str = field(metadata=config(letter_case=LetterCase.KEBAB))
    results_json_upload_url: Optional[str] = None
    results_csv_upload_url: Optional[str] = None
    results_to_show: Optional[ProviderURLField] = None
    result_to_show: Optional[ProviderURLField] = None  # TODO: remove backward compatibility


@dataclass_json
@dataclass
class AlgorithmPredictRequest:
    request_id: Optional[str] = None
    tenant_uuid: Optional[str] = None
    task_name: Optional[str] = None
    algorithm_type: Optional[str] = None
    results_to_show: Optional[bool] = None
    # results_to_show_upload_url: Optional[str] = None  # TODO: remove backward compatibility
    results_files_upload_url: Optional[List[ProviderURLField]] = None
    output_mimes: Optional[List[str]] = None
    options: Optional[dict] = None
    params: Optional[dict] = None
    data: Optional[List[UploadDataField]] = None
    callback_url: Optional[str] = None


@dataclass_json
@dataclass
class AlgorithmPredictCallback:
    id: str
    success: bool
    task_name: Optional[str] = None
    count: Optional[int] = None
    results: Optional[Any] = None
    metrics: Optional[List[Any]] = None
    tenant_uuid: Optional[str] = None
