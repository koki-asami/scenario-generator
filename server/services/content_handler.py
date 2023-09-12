import io
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, List, Tuple

import cv2
import numpy as np
import requests
from PIL import Image
from requests_futures.sessions import FuturesSession
from requests_testadapter import Resp
from vidgear.gears import WriteGear

from domain.predict_domain import TYPE_FILE, TYPE_IMAGE, UploadDataField
from exceptions import InvalidParameterError, NotFound, Timeout
from services.utils import MP4, mime2ext, mime2format

logger = logging.getLogger(__name__)


def file_to_frames(file) -> np.ndarray:
    return np.array(Image.open(file).convert('RGB'))


def frame_to_file(frame, format='JPEG') -> BinaryIO:
    img = Image.fromarray(frame)
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def timeout_seconds(timeout_at):
    if timeout_at is None:
        return None
    return (timeout_at - datetime.now()).total_seconds()


def create_handler(message, files: dict = None, timeout_at=None, pool=None):
    if len(message.data) == 0:
        raise InvalidParameterError('data is empty')
    if message.algorithm_type == TYPE_IMAGE and len(message.data) > 1:
        raise InvalidParameterError('algorithm_type:image only supports 1 data')
    # create handler
    if message.algorithm_type == TYPE_FILE:
        return FileHandler(message.data, message.options, timeout_at=timeout_at, pool=pool)
    if str(message.data[0].content_type).startswith('video/'):
        if len(message.data) > 1:
            raise InvalidParameterError('algorithm_type:simple, video only supports 1 data')
        return VideoHandler(message.data, message.options, timeout_at=timeout_at)
    if str(message.data[0].content_type).startswith('image/'):
        return ImageHandler(message.data, message.options, timeout_at=timeout_at, pool=pool)
    raise InvalidParameterError(f'invalid content type: {message.data[0].content_type}')


class LocalFileAdapter(requests.adapters.HTTPAdapter):
    def build_response_from_file(self, request: requests.PreparedRequest):
        file_path = request.url[7:]
        if request.method == 'GET':
            with open(file_path, 'rb') as file:
                buff = bytearray(os.path.getsize(file_path))
                file.readinto(buff)
        else:
            buff = request.body.getvalue()
            with open(file_path, 'wb') as file:
                file.write(buff)
        resp = Resp(buff)
        r = self.build_response(request, resp)
        return r

    def send(self, request, stream=False, timeout=None,
             verify=True, cert=None, proxies=None):
        return self.build_response_from_file(request)


class VideoHandler:
    """TYPE_SIMPLE(video)でframe分解を行う"""

    def __init__(self, data_list, options, timeout_at=None):
        self._data_list = data_list
        self._options = options
        self._timeout_at = timeout_at

    def download_frame_or_files(self, files=None) -> Tuple[list, int]:
        reader = self._get_reader(files)
        self._frames = self._get_video_option('frames', self._get_frames(reader))
        # setup params for upload_frames
        original_fps = int(reader.get(cv2.CAP_PROP_FPS))
        # target fps
        self._fps = int(self._get_video_option('fps', original_fps))
        if original_fps < self._fps:
            # support only frame reduction.
            self._fps = original_fps
        self._width = int(reader.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(reader.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f'download videoframes({len(self._frames)}) {self._fps=} {original_fps=}')

        images = []
        if len(self._frames) > 0:
            frame_consumed_count = 0
            reader.set(cv2.CAP_PROP_POS_FRAMES, self._frames[0])
            for idx in self._frames:
                ok, frame = reader.read()
                if not ok:
                    logger.warning(f'video frame {idx} is not found.')
                    # safieの壊れた動画の場合、CAP_PROP_POS_FRAMESをセットすると動画フレームが取得できないのでreaderを再取得して処理続行する
                    if idx == 0:
                        reader = self._get_reader(files)
                        ok, frame = reader.read()
                    if not ok:
                        self._frames = range(idx)
                        break
                    logger.info('video reader reopened.')

                frame_consumed_count += self._fps
                # frame reduction if params.fps(target fps) is set.
                if self._fps == original_fps or int(frame_consumed_count / original_fps) >= len(images):
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    images.append(frame)

        return images, self._fps

    def upload_frames(self, images):
        if not self._data_list[0].results_to_show:
            return [False] * len(images)

        output_params = {
            '-vcodec': 'libx264',
            '-input_framerate': self._fps,
            '-output_dimensions': (int(self._width), int(self._height)),
            '-preset': 'ultrafast',
            '-pix_fmt': 'yuv420p',
        }

        suffix = mime2ext(self._data_list[0].results_to_show.content_type)
        with tempfile.NamedTemporaryFile(suffix=suffix) as result_file:
            writer = WriteGear(output=result_file.name, compression_mode=True, logging=False, **output_params)

            for img in images:
                writer.write(img, rgb_mode=True)

            # finish up video file
            writer.close()
            result_file.seek(0)

            # upload video file
            timeout = timeout_seconds(self._timeout_at)
            if timeout and timeout < 0:
                raise Timeout(timeout)
            res = requests.put(self._data_list[0].results_to_show.url, result_file, timeout=timeout)
            res.raise_for_status()

        # if upload fails then return 500 error
        return [True] * len(images)

    def _download_video(self):
        timeout = timeout_seconds(self._timeout_at)
        if timeout and timeout < 0:
            raise Timeout(timeout)
        # download video and load to cv2.VideoCapture
        try:
            with requests.get(self._data_list[0].url, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                with tempfile.NamedTemporaryFile(suffix=mime2ext(self._data_list[0].content_type)) as f:
                    shutil.copyfileobj(r.raw, f)
                    reader = cv2.VideoCapture(f.name)
        except requests.exceptions.Timeout as e:
            raise Timeout(e)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise NotFound(e)
            raise

        if not reader.isOpened():
            raise InvalidParameterError

        return reader

    def _get_video_option(self, name, default=None):
        return self._options.get('video', {}).get(name, default)

    def _get_reader(self, files=None) -> cv2.VideoCapture:
        if files:
            try:
                suffix = mime2ext(self._data_list[0].content_type)
            except Exception:
                suffix = mime2ext(MP4)
            with tempfile.TemporaryDirectory() as td:
                temp_filename = Path(td) / f'uploaded_video{suffix}'
                list(files.values())[0].save(temp_filename)
                reader = cv2.VideoCapture(str(temp_filename))
        else:
            reader = self._download_video()
        return reader

    def _get_frames(self, reader):
        # ref: https://stackoverflow.com/questions/49048111/how-to-get-the-duration-of-video-using-cv2
        # set frame cursor to last frame
        reader.set(cv2.CAP_PROP_POS_AVI_RATIO, 1)
        # CAP_PROP_POS_FRAMESはsafieで信用出来ない値になる場合がある
        frames = int(reader.get(cv2.CAP_PROP_POS_FRAMES))
        frame_count = int(reader.get(cv2.CAP_PROP_FRAME_COUNT))
        return range(frames) if frames < frame_count else range(frame_count)


class BaseHandler:
    def __init__(self, data_list, options, timeout_at=None, pool=None):
        self._data_list = data_list
        self._options = options
        self._timeout_at = timeout_at
        self._session = FuturesSession(executor=pool)
        self._session.mount('file://', LocalFileAdapter())

    def download_frame_or_files(self, files=None) -> Tuple[list, int]:
        if files:
            return self._get_data_from_files(files), None
        else:
            timeout = timeout_seconds(self._timeout_at)
            if timeout and timeout < 0:
                raise Timeout(timeout)
            frame_or_files = [
                self._get_data(self._session.get(data.url, stream=True, timeout=timeout), data)
                for data in self._data_list
            ]
            return frame_or_files, None

    def upload_frames(self, images):
        uploaded = []
        for data, img in zip(self._data_list, images):
            if not data.results_to_show:
                # not upload result image
                uploaded.append(None)
                continue

            # generate image
            result_format = mime2format(data.results_to_show.content_type)
            img = frame_to_file(img, format=result_format)

            # upload results_to_show
            res = self._session.put(data.results_to_show.url, img, timeout=timeout_seconds(self._timeout_at))
            uploaded.append(res)

        return [self._success_upload(u) for u in uploaded]

    def _get_data(self, future, data: List[UploadDataField]) -> Any:
        raise NotImplementedError

    def _success_upload(self, future):
        if future is None:
            return False
        timeout = timeout_seconds(self._timeout_at)
        try:
            resp = future.result(timeout=timeout)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(e, exc_info=True)
            return False


class FileHandler(BaseHandler):
    def __init__(self, data_list, options, timeout_at=None, pool=None):
        super().__init__(data_list, options, timeout_at, pool)

    def _get_data(self, future, data: List[UploadDataField]) -> BinaryIO:
        timeout = timeout_seconds(self._timeout_at)
        try:
            resp = future.result(timeout=timeout)
            resp.raise_for_status()
            # tempfileは終了と同時に自動で削除される
            file = tempfile.NamedTemporaryFile(suffix=mime2ext(data.content_type))
            shutil.copyfileobj(resp.raw, file)
            file.seek(0)
            return file
        except Exception as e:
            raise NotFound(str(e))

    def _get_data_from_files(self, files) -> list:
        return list(files.values())


class ImageHandler(BaseHandler):
    def __init__(self, data_list, options, timeout_at=None, pool=None):
        super().__init__(data_list, options, timeout_at, pool)

    def _get_data(self, future, data: List[UploadDataField]) -> BinaryIO:
        timeout = timeout_seconds(self._timeout_at)
        try:
            resp = future.result(timeout=timeout)
            resp.raise_for_status()
            return np.array(Image.open(resp.raw).convert('RGB'))
        except Exception as e:
            raise NotFound(str(e))

    def _get_data_from_files(self, files) -> list:
        return [file_to_frames(file) for file in files.values()]
