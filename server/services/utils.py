import csv
import itertools
import re

import cv2
import numpy as np

from exceptions import InvalidDataType  # noqa


class FieldConflictError(ValueError):
    pass


DELIM_REGEX = re.compile(r'(\.|\[\d*\]|\[id\])')
INDEX_REGEX = re.compile(r'\A\[(\d+)\]\Z')
KEY_ARRAY = '[]'
KEY_ARRAY_ID = '[id]'
KEY_ID = 'id'

PNG = 'image/png'
JPEG = 'image/jpeg'

IMAGES = [PNG, JPEG]

AVI = 'video/x-msvideo'
MOV = 'video/quicktime'
WMV = 'video/x-ms-wmv'
ASF = 'video/x-ms-asf'
FLV = 'video/x-flv'
MP4 = 'video/mp4'
MPEG = 'video/mpeg'
MPEGTS = 'video/mp2t'

MP3 = 'audio/mpeg'
AUDIO_MP4 = 'audio/mp4'
AAC = 'audio/aac'
WAVE = 'audio/wav'

VIDEOS = [AVI, MOV, WMV, FLV, MP4, MPEG, MPEGTS]

JSON = 'application/json'
CSV = 'text/csv'
TXT = 'text/plain'
ZIP = 'application/zip'

MIME2EXT = {
    PNG: '.png',
    JPEG: '.jpg',
    AVI: '.avi',
    MOV: '.mov',
    WMV: '.wmv',
    ASF: '.asf',
    FLV: '.flv',
    MP4: '.mp4',
    MPEG: '.mpg',
    MPEGTS: '.ts',
    MP3: '.mp3',
    AUDIO_MP4: '.m4a',
    AAC: '.m4a',
    WAVE: '.wav',
    JSON: '.json',
    CSV: '.csv',
    TXT: '.txt',
    ZIP: '.zip',
}

MIME2FORMAT = {
    PNG: 'PNG',
    JPEG: 'JPEG',
}


def mime2ext(mime):
    try:
        return MIME2EXT[mime]
    except KeyError:
        raise InvalidDataType(mime=mime)


def mime2format(mime):
    try:
        return MIME2FORMAT[mime]
    except KeyError:
        raise InvalidDataType(mime=mime)


def byte2np(npbyte):
    image = cv2.imdecode(npbyte, cv2.IMREAD_COLOR)

    if image.ndim == 2:
        pass
    elif image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)

    return image


def get_image_from_file_storage(file_storage):
    if file_storage.filename != '':
        npbyte = np.asarray(bytearray(file_storage.stream.read()), dtype=np.uint8)
        image = byte2np(npbyte)
    else:
        raise ValueError('`filename` must not be empty.')

    return image


def get_inputs_from_request(api_request):
    if 'file' in api_request.files.keys():
        # multipart/form-data: in case request has `files`
        uploaded_files = api_request.files.getlist('file')
        inputs = []
        filename_list = []
        for _file in uploaded_files:
            inputs.append(get_image_from_file_storage(_file))
            filename_list.append(_file.filename)

    elif hasattr(api_request, 'data'):
        # base64: in case request has `data`
        # note that only one image request is supported.
        npbyte = np.fromstring(api_request.data, np.uint8)
        inputs = byte2np(npbyte)
        filename_list = []

    else:
        raise ValueError('there is no option for this request.')

    return inputs, filename_list


def parse_index(v: str):
    match = INDEX_REGEX.fullmatch(v)
    return int(match[1]) if match else v


def parse_key(key: str):
    parsed = DELIM_REGEX.split(key)
    parsed = filter(lambda v: v != '' and v != '.', parsed)
    parsed = map(parse_index, parsed)
    return list(parsed)


def build_array_fields(keys, fields):
    max_depth = max(map(len, fields.values()), default=0)
    array_fields = []
    prev_prefixes = []
    prev_depth = 0
    for depth in range(max_depth):
        prefixes = []
        render_fields = []
        for name in keys:
            if len(fields[name]) <= depth:
                continue
            if fields[name][depth] != KEY_ARRAY:
                continue

            # check array prefix conflict
            prefix = fields[name][:depth]
            if len(prev_prefixes) > 0 and prefix[prev_depth] != KEY_ARRAY:
                raise FieldConflictError(f'{name} conflicts level {prev_depth} is not array')
            if len(prev_prefixes) > 0 and prefix[:prev_depth] not in prev_prefixes:
                raise FieldConflictError(f'{name} conflicts array at {depth}')

            # "[id]" not add to array_fields but check conflict
            if KEY_ARRAY_ID in fields[name]:
                continue

            # add prefix
            if prefix not in prefixes:
                prefixes.append(prefix)
            if KEY_ARRAY not in fields[name][depth + 1:]:
                render_fields.append((name, fields[name]))

        if len(prefixes) > 0:
            array_fields.append((prefixes, render_fields))
            prev_prefixes = prefixes
            prev_depth = depth
    return array_fields


def build_array_id_fields(fields, array_fields):
    id_fields = [[] for _ in array_fields]
    for name, field in fields.items():
        try:
            idx = field.index(KEY_ARRAY_ID)
        except ValueError:
            # "[id]" is not included in this field
            continue

        # "[id]" must come last of field name
        if idx + 1 != len(field):
            raise FieldConflictError(f'{name} includes invalid [id]')

        match = False
        for id_field, (arrays, _) in zip(id_fields, array_fields):
            if len(arrays[0]) != idx:
                # level not match
                continue
            if field[:idx] not in arrays:
                raise FieldConflictError(f'{name} prefix not match')
            id_field.append(name)
            match = True
        if not match:
            raise FieldConflictError(f'{name} not match any array')
    return id_fields


class NestedDictWriter:
    def __init__(self, f, fieldnames, raise_on_missing=False, restval='', *args, **kwargs):
        self._writer = csv.DictWriter(f, fieldnames, restval=restval, *args, **kwargs)
        self.restval = restval
        self.raise_on_missing = raise_on_missing
        self._fields = {name: parse_key(name) for name in fieldnames}
        self._simple_fields = {k: field for (k, field) in self._fields.items() if
                               KEY_ARRAY not in field and KEY_ARRAY_ID not in field}
        self._array_fields = build_array_fields(fieldnames, self._fields)
        self._array_id_fields = build_array_id_fields(self._fields, self._array_fields)

    def writeheader(self):
        self._writer.writeheader()

    def writerow(self, rowdict, id=None):
        current = {}
        if id is not None:
            current['id'] = id

        for key, field in self._simple_fields.items():
            if key == 'id' and id is not None:
                v = self._get_value(rowdict, field)
                v = id if v == self.restval else v
                current[key] = v
            else:
                current[key] = self._get_value(rowdict, field)

        # if simple_fields only
        if len(self._array_fields) == 0:
            return self._writer.writerow(current)

        # pre-calcurate loop count
        loop_counts = map(lambda array_field: array_field[0], self._array_fields)
        loop_counts = map(lambda prefixes: map(lambda prefix: self._get_max_loop(rowdict, prefix), prefixes),
                          loop_counts)
        loop_counts = map(lambda field_max_loop: max(field_max_loop), loop_counts)
        # render simple fields even if array is empty
        loop_counts = [n if n > 0 else 1 for n in loop_counts]

        # render
        prev_indexes = [-1] * len(self._array_fields)
        for indexes in itertools.product(*map(lambda n: range(n), loop_counts)):
            # render array ids
            for i, id_fields in zip(indexes, self._array_id_fields):
                for key in id_fields:
                    current[key] = i

            changed = False
            # render array element only after changed array element
            for i, prev, (_, render_fields) in zip(indexes, prev_indexes, self._array_fields):
                if changed or i != prev:
                    changed = True
                    for key, field in render_fields:
                        current[key] = self._get_value(rowdict, field, array_index=indexes)
            self._writer.writerow(current)
            prev_indexes = indexes

    def writerows(self, rowdicts, first_id=None):
        id = first_id
        for rowdict in rowdicts:
            self.writerow(rowdict, id=id)
            if first_id is not None:
                id += 1

    def _get_value(self, rowdict, field, array_index=None):
        v = rowdict
        for k in field:
            if k == KEY_ARRAY:
                idx = array_index[0]
                array_index = array_index[1:]
                try:
                    v = v[idx]
                except IndexError:
                    return self.restval
            else:
                if self.raise_on_missing:
                    v = v[k]
                else:
                    try:
                        v = v[k]
                    except (IndexError, KeyError, TypeError):
                        return self.restval
        return v

    def _get_max_loop(self, rowdict, field):
        v = rowdict
        for i in range(len(field)):
            key = field[i]
            if key == KEY_ARRAY:
                return max(map(lambda elem: self._get_max_loop(elem, field[i + 1:]), v), default=0)
            else:
                if self.raise_on_missing:
                    v = v[key]
                else:
                    try:
                        v = v[key]
                    except (IndexError, KeyError, TypeError):
                        return 0
        return len(v)


def generate_fieldnames(value, prefix=''):
    fieldnames = []
    if isinstance(value, dict):
        prefix = prefix + '.' if prefix != '' else ''
        for key in sorted(value.keys()):
            subnames = generate_fieldnames(value[key], prefix=f'{prefix}{key}')
            fieldnames.extend(subnames)
    elif isinstance(value, list):
        # NOTICE: list support is NOT reliable
        subnames = [f'{prefix}[id]']
        if len(value) > 0:
            subnames += generate_fieldnames(value[0], prefix=f'{prefix}[]')
        else:
            subnames += [f'{prefix}[]']
        fieldnames.extend(subnames)
    else:
        fieldnames.append(prefix)
    return fieldnames
