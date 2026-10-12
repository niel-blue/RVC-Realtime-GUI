"""Per-process capture using the shared Audio-Bridge Windows implementation."""
import ctypes as c
import threading
import time
from pathlib import Path
import numpy as np

class ApplicationSource:
    def __init__(self):
        self.dll = c.CDLL(str(Path(__file__).parent / 'application_capture' / 'application_capture.dll'))
        d = self.dll
        d.app_list.argtypes = [c.c_char_p, c.c_int]
        d.app_create.restype = c.c_void_p
        d.app_start.argtypes = [c.c_void_p, c.c_uint, c.c_double]
        d.app_read.argtypes = [c.c_void_p, c.c_void_p, c.c_void_p, c.c_int]
        d.app_destroy.argtypes = [c.c_void_p]
        d.app_error.argtypes = [c.c_void_p, c.c_char_p, c.c_int]
        d.app_resolve.argtypes = [c.c_char_p]
        d.app_resolve.restype = c.c_uint
        self.thread = None
        self.stop_event = threading.Event()
        self.error = None

    def enumerate(self):
        buffer = c.create_string_buffer(262144)
        if self.dll.app_list(buffer, len(buffer)) < 0:
            raise RuntimeError('Could not enumerate application audio sessions')
        return [line.split('\t', 2) for line in buffer.value.decode('utf-8').splitlines()]

    def resolve(self, identity):
        return self.dll.app_resolve(identity.encode('utf-8'))

    def start(self, pid, rate, frames, callback, identity=''):
        self.stop()
        handle = self.dll.app_create()
        if not self.dll.app_start(handle, int(pid), rate):
            buffer = c.create_string_buffer(4096)
            self.dll.app_error(handle, buffer, len(buffer))
            self.dll.app_destroy(handle)
            raise RuntimeError(buffer.value.decode('utf-8') or 'Application capture unavailable')
        self.stop_event.clear()
        self.error = None
        def run():
            nonlocal handle, pid
            left = np.zeros(frames, dtype=np.float32)
            right = np.zeros_like(left)
            deadline = time.perf_counter()
            check_due = deadline + 1
            try:
                while not self.stop_event.is_set():
                    if identity and time.perf_counter() >= check_due:
                        current = self.resolve(identity)
                        if current != pid:
                            self.dll.app_destroy(handle)
                            handle = self.dll.app_create()
                            pid = current
                            if pid and not self.dll.app_start(handle, pid, rate):
                                raise RuntimeError('Could not reconnect application input')
                        check_due = time.perf_counter() + 1
                    self.dll.app_read(handle, left.ctypes.data, right.ctypes.data, frames)
                    callback(((left + right) * 0.5)[:, None], frames, None, None)
                    deadline += frames / rate
                    self.stop_event.wait(max(0, deadline-time.perf_counter()))
            except Exception as error:
                self.error = str(error)
            finally:
                self.dll.app_destroy(handle)
        self.thread = threading.Thread(target=run, name='rvc-application-input', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join()
            self.thread = None
