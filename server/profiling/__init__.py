import gc
import logging
import os
import time
from threading import Thread

from torch import cuda

from .mem_info import MemoryInfo, ProcessMemoryInfo, humanSize

logger = logging.getLogger(__name__)


class MemProfiler:
    def __init__(self, interval=0.001):
        self._profiling = False
        self._interval = interval

        self.machine_mem = MemoryInfo()
        self.machine_thread = None
        self.initial_machine_available = 0
        self.peak_machine_available = 0

        self.cpu_mem = ProcessMemoryInfo(os.getpid())
        self.initial_cpu_mem = 0
        self.peak_cpu_mem = 0

        self.gpu_available = cuda.is_available()
        self.initial_gpu_mem = 0
        self.peak_gpu_mem = 0

    def start(self):
        gc.collect()
        self._profiling = True

        # setup machine mem
        self.machine_mem.update()
        self.initial_machine_available = self.machine_mem['MemAvailable']
        self.peak_machine_available = self.initial_machine_available
        self.machine_thread = Thread(target=self._machine_mem_loop)
        self.machine_thread.start()

        # setup process cpu
        self.cpu_mem.clear_refs()
        self.cpu_mem.update()
        self.initial_cpu_mem = self.cpu_mem['VmHWM']

        # setup gpu
        if self.gpu_available:
            cuda.reset_max_memory_allocated()
            self.initial_gpu_mem = cuda.max_memory_allocated()

    def finish(self):
        self._profiling = False

        self.machine_thread.join()
        self._update_machine_mem()

        self.cpu_mem.update()
        self.peak_cpu_mem = self.cpu_mem['VmHWM']

        if self.gpu_available:
            self.peak_gpu_mem = cuda.max_memory_allocated()

    def output(self):
        logger.warning('min_machine  : %s' % humanSize(self.peak_machine_available))
        logger.warning('machine_mem  : %s' % humanSize(self.initial_machine_available - self.peak_machine_available))
        logger.warning('max_cpu_mem  : %s' % humanSize(self.peak_cpu_mem))
        logger.warning('cpu_mem_usage: %s' % humanSize(self.peak_cpu_mem - self.initial_cpu_mem))
        logger.warning('max_gpu_mem  : %s' % humanSize(self.peak_gpu_mem))
        logger.warning('gpu_mem_usage: %s' % humanSize(self.peak_gpu_mem - self.initial_gpu_mem))

    def _machine_mem_loop(self):
        while self._profiling:
            self._update_machine_mem()
            time.sleep(self._interval)

    def _update_machine_mem(self):
        self.machine_mem.update()
        v = self.machine_mem['MemAvailable']
        if v < self.peak_machine_available:
            self.peak_machine_available = v


class TimeProfiler:
    def __init__(self):
        self._start_at = None
        self._current = None

    def start(self):
        self._start_at = time.perf_counter()
        self._current = self._start_at

    def tic(self, label):
        now = time.perf_counter()
        diff = now - self._current
        self._current = now
        logger.warning(f'{label} : {diff}s')

    def finish(self):
        now = time.perf_counter()
        diff = now - self._start_at
        logger.warning(f'finish : total {diff}s')
