import inspect
import functools
import threading
from contextlib import contextmanager


class ReadWriteLock:
    def __init__(self):
        self._lock = threading.Lock()
        self._read_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._read_count = 0
        self._write_owner = None

    def acquire_read(self):
        with self._lock:
            self._read_count += 1
            if self._read_count == 1:
                self._write_lock.acquire()
        self._read_lock.acquire()

    def release_read(self):
        self._read_lock.release()
        with self._lock:
            self._read_count -= 1
            if self._read_count == 0:
                self._write_lock.release()

    def acquire_write(self):
        self._write_lock.acquire()
        self._write_owner = threading.current_thread().ident

    def release_write(self):
        if self._write_owner == threading.current_thread().ident:
            self._write_owner = None
        self._write_lock.release()

    @contextmanager
    def read_lock(self):
        if self._write_owner == threading.current_thread().ident:
            yield
            return
        self.acquire_read()
        try:
            yield
        finally:
            self.release_read()

    @contextmanager
    def write_lock(self):
        if self._write_owner == threading.current_thread().ident:
            yield
            return
        self.acquire_write()
        try:
            yield
        finally:
            self.release_write()


ATTR_NAME = f'{__name__}_rwlock'


def with_RW_lock(cls):
    assert not hasattr(cls, ATTR_NAME), f'Failed to add RW lock since class "{cls}" uses required attribute {ATTR_NAME}'
    setattr(cls, ATTR_NAME, ReadWriteLock())
    return cls


def read_lock(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # need_acquire = not is_write_lock_acquired()

        # import logging
        # logging.error(f'read_lock / need_acquire = {need_acquire}')
        # logging.error("Current call stack:")
        # for frame_info in inspect.stack():
        #     frame = frame_info[0]
        #     filename = frame.f_code.co_filename
        #     lineno = frame.f_lineno
        #     function_name = frame.f_code.co_name
        #     logging.error(f"  File '{filename}', line {lineno}, in {function_name}")

        # if need_acquire:
        rwlock: ReadWriteLock = getattr(self, ATTR_NAME)
        with rwlock.read_lock():
            return func(self, *args, **kwargs)
    return wrapper


def write_lock(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # need_acquire = not is_write_lock_acquired()

        # import logging
        # logging.error(f'write_lock / need_acquire = {need_acquire}')
        # logging.error("Current call stack:")
        # for frame_info in inspect.stack():
        #     frame = frame_info[0]
        #     filename = frame.f_code.co_filename
        #     lineno = frame.f_lineno
        #     function_name = frame.f_code.co_name
        #     logging.error(f"  File '{filename}', line {lineno}, in {function_name}")

        # if wrapper.acquired:
        #     return func(self, *args, **kwargs)
        rwlock: ReadWriteLock = getattr(self, ATTR_NAME)
        with rwlock.write_lock():
            return func(self, *args, **kwargs)
    return wrapper
