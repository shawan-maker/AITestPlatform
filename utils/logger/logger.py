# utils/logger/logger.py
"""
线程安全 stdout 替换类

用于多线程并发场景下的输出隔离：
  - 使用 threading.local() 为每个线程维护独立的 StringIO buffer
  - 主线程（未设置 buffer）：直接写入原始 stdout
  - 工作线程（已设置 buffer）：写入各自的 StringIO buffer
"""

import threading


class _ThreadSafeStdout:
    """
    线程安全的 stdout 替换类
    使用 threading.local() 为每个线程维护独立的 StringIO buffer
    - 主线程（未设置 buffer）：直接写入原始 stdout
    - 工作线程（已设置 buffer）：写入各自的 StringIO buffer
    """
    def __init__(self, original):
        self._original = original
        self._local = threading.local()

    def set_buffer(self, buf):
        """为当前线程设置输出 buffer"""
        self._local.buffer = buf

    def write(self, data):
        buf = getattr(self._local, 'buffer', None)
        if buf is not None:
            buf.write(data)
        else:
            self._original.write(data)

    def flush(self):
        buf = getattr(self._local, 'buffer', None)
        if buf is not None:
            buf.flush()
        else:
            self._original.flush()

    def __getattr__(self, name):
        """委托其他属性到原始 stdout（如 encoding、errors 等）"""
        return getattr(self._original, name)
