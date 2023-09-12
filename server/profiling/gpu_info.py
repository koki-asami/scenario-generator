# https://www.kaggle.com/competitions/foursquare-location-matching/discussion/336462
# trace取得に一回200msかかる。本番提供では呼び出す回数に注意。

import logging
import math
import os
import subprocess
import time
from contextlib import contextmanager

import numpy as np
import psutil
import torch

logger = logging.getLogger(__name__)


def get_gpu_memory(cmd_path='nvidia-smi', target_properties=('memory.total', 'memory.used')):
    """
    ref: https://www.12-technology.com/2022/01/pythongpu.html
    Returns
    -------
    gpu_total : ndarray,  "memory.total"
    gpu_used: ndarray, "memory.used"
    """

    # format option
    format_option = '--format=csv,noheader,nounits'

    cmd = '%s --query-gpu=%s %s' % (cmd_path, ','.join(target_properties), format_option)

    # Command execution in sub-processes
    cmd_res = subprocess.check_output(cmd, shell=True)

    gpu_lines = cmd_res.decode().split('\n')[0].split(', ')

    gpu_total = int(gpu_lines[0]) / 1024
    gpu_used = int(gpu_lines[1]) / 1024

    gpu_total = np.round(gpu_used, 1)
    gpu_used = np.round(gpu_used, 1)
    return gpu_total, gpu_used


class Trace:
    def __init__(self, gpu_profile):
        self.cuda = gpu_profile and torch.cuda.is_available()

    @contextmanager
    def timer(self, title):
        t0 = time.time()
        p = psutil.Process(os.getpid())
        cpu_m0 = p.memory_info().rss / 2.0**30
        if self.cuda:
            gpu_m0 = get_gpu_memory()[0]
        yield
        cpu_m1 = p.memory_info().rss / 2.0**30
        if self.cuda:
            gpu_m1 = get_gpu_memory()[0]

        cpu_delta = cpu_m1 - cpu_m0
        if self.cuda:
            gpu_delta = gpu_m1 - gpu_m0

        cpu_sign = '+' if cpu_delta >= 0 else '-'
        cpu_delta = math.fabs(cpu_delta)

        if self.cuda:
            gpu_sign = '+' if gpu_delta >= 0 else '-'
        if self.cuda:
            gpu_delta = math.fabs(gpu_delta)

        cpu_message = f'{cpu_m1:.1f}GB({cpu_sign}{cpu_delta:.1f}GB)'
        if self.cuda:
            gpu_message = f'{gpu_m1:.1f}GB({gpu_sign}{gpu_delta:.1f}GB)'

        if self.cuda:
            message = f'[cpu: {cpu_message}, gpu: {gpu_message}: {time.time() - t0:.1f}sec] {title} '
        else:
            message = f'[cpu: {cpu_message}: {time.time() - t0:.1f}sec] {title} '

        logger.info(message)
