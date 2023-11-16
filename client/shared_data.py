import threading
from collections import deque
from typing import Iterable
from proto import mafia_pb2


ROOM_INFO = None
ROOM_INFO_HISTORY = deque()
MAX_ROOM_INFO_HISTORY_SIZE = 20
_lock = threading.Lock()


def get_room_info():
    with _lock:
        return ROOM_INFO


def get_room_info_history():
    with _lock:
        return ROOM_INFO_HISTORY


def set_room_info(room_info):
    global ROOM_INFO, ROOM_INFO_HISTORY
    with _lock:
        if room_info != ROOM_INFO:
            ROOM_INFO = room_info
            # NOTE: No reason found to use room info history yet
            # if len(ROOM_INFO_HISTORY) == MAX_ROOM_INFO_HISTORY_SIZE:
            #     ROOM_INFO_HISTORY.popleft()
            # ROOM_INFO_HISTORY.append(room_info)


def poll_room_info(response: Iterable[mafia_pb2.Room], stop=lambda: False):
    while not stop():
        try:
            room_info = next(response)
            set_room_info(room_info)
        except Exception:
            return
    response.cancel()


CURRENT_PROMPT = None
_prompt_lock = threading.Lock()


def get_current_prompt():
    with _prompt_lock:
        return CURRENT_PROMPT


def set_current_prompt(current_prompt):
    global CURRENT_PROMPT
    with _prompt_lock:
        CURRENT_PROMPT = current_prompt
