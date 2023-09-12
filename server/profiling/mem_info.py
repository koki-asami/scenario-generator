# ref: https://gist.github.com/matteobertozzi/1340799

def _procMemoryGrep(filename, vmkeys):  # NOQA N802
    size_scale = {'kb': 1024.0, 'mb': 1048576.0, 'gb': 1073741824.0}
    values = {}

    fd = open(filename)
    try:
        for line in fd:
            for vmkey in vmkeys:
                if vmkey in line:
                    _, size, scale = line.split()
                    scale = size_scale.get(scale.strip().lower(), 1)
                    values[vmkey] = float(size.strip()) * scale
    finally:
        fd.close()

    return values


class ProcessMemoryInfo(object):
    _KEYS = [
        'VmPeak',  # peak virtual memory size
        'VmSize',  # total program size
        'VmLck',  # locked memory size
        'VmHWM',  # peak resident set size ("high water mark")
        'VmRSS',  # size of memory portions
        'VmData',  # size of data, stack, and text segments
        'VmStk',  # size of data, stack, and text segments
        'VmExe',  # size of text segment
        'VmLib',  # size of shared library code
        'VmPTE',  # size of page table entries
        'VmSwap',  # size of swap usage (the number of referred swapents)
    ]

    def __init__(self, proc):
        self.pid = proc
        self._status = {}
        self.update()

    def __getitem__(self, key):
        return self._status[key]

    def update(self):
        self._status = _procMemoryGrep('/proc/%d/status' % self.pid, self._KEYS)

    def clear_refs(self, value=5):
        """
        /proc/[pid]/clear_refs (since Linux 2.6.22)
        http://man7.org/linux/man-pages/man5/proc.5.html

        1 (since Linux 2.6.22)
             Reset the PG_Referenced and ACCESSED/YOUNG bits for all
             the pages associated with the process.  (Before kernel
             2.6.32, writing any nonzero value to this file had this
             effect.)

        2 (since Linux 2.6.32)
             Reset the PG_Referenced and ACCESSED/YOUNG bits for all
             anonymous pages associated with the process.

        3 (since Linux 2.6.32)
             Reset the PG_Referenced and ACCESSED/YOUNG bits for all
             file-mapped pages associated with the process.
        4 (since Linux 3.11)
             Clear the soft-dirty bit for all the pages associated
             with the process.  This is used (in conjunction with
             /proc/[pid]/pagemap) by the check-point restore system
             to discover which pages of a process have been dirtied
             since the file /proc/[pid]/clear_refs was written to.

        5 (since Linux 4.0)
             Reset the peak resident set size ("high water mark") to
             the process's current resident set size value.
        """
        with open('/proc/%d/clear_refs' % self.pid, mode='w') as f:
            f.write('%d' % value)


class MemoryInfo(object):
    """
    http://man7.org/linux/man-pages/man5/proc.5.html
    """
    _KEYS = [
        'MemTotal',  # Total usable RAM
        'MemFree',  # The sum of LowFree+HighFree
        'MemAvailable',  # An estimate of how much memory is available for starting new applications, without swapping.
        'Buffers',  # Relatively temporary storage for raw disk blocks that shouldn't get tremendously large
        'Cached',  # In-memory cache for files read from the disk
        'SwapCached',  # Memory that once was swapped out, is swapped back in but still also is in the swap file
        'Active',  # Memory that has been used more recently and usually not reclaimed unless absolutely necessary
        'Inactive',  # Memory which has been less recently used.  It is more eligible to be reclaimed for other purposes
    ]

    def __init__(self):
        self._status = {}
        self.update()

    def __getitem__(self, key):
        return self._status[key]

    def update(self):
        self._status = _procMemoryGrep('/proc/meminfo', self._KEYS)


def humanSize(size):  # NOQA N802
    human = ((1 << 80, 'YiB'),
             (1 << 70, 'ZiB'),
             (1 << 60, 'EiB'),
             (1 << 50, 'PiB'),
             (1 << 40, 'TiB'),
             (1 << 30, 'GiB'),
             (1 << 20, 'MiB'),
             (1 << 10, 'KiB'))
    for t, s in human:
        if size >= t:
            return '%.2f %s' % ((size / t), s)
    return '%d bytes' % size
