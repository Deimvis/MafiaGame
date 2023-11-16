import threading
import re
import rich.console
from collections import defaultdict
from rich.style import Style

from client.shared_data import get_room_info


class GlobalConsole:
    def __init__(self):
        self.lock = threading.Lock()
        self.console = rich.console.Console()

    def print(self, msg, style=None):
        if style is None:
            self.console.print(style_message(msg))
        else:
            self.console.print(msg, style=style)

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self ,type, value, traceback):
        self.lock.release()


global_console = GlobalConsole()


def style_message(message: str):
    message = _color_usernames(message)
    message = _replace_with_style(message, 'Mafia', style=Style(color='#DC113A', bold=True))
    message = _replace_with_style(message, 'Civilian', style=Style(color='#14EE6B', bold=True))
    message = _replace_with_style(message, 'Sheriff', style=Style(color='#0D85EE', bold=True))
    message = _replace_with_style(message, '>', style=Style(color='#E54670'))
    message = _replace_with_style(message, 'DEAD', style=Style(color='#620C0C'))
    message = _replace_with_style(message, 'EXPOSED', style=Style(color='#B14CFF'))
    message = _replace_with_style(message, 'DAY', style=Style(color='#FF1810'))
    message = _replace_with_style(message, 'Day phase', style=Style(color='#E7FF4C'))
    message = _replace_with_style(message, 'Night phase', style=Style(color='#6A4CFF'))
    return message


def _color_usernames(text: str) -> str:
    room_info = get_room_info()
    username2style = defaultdict(lambda: Style())
    for player in room_info.Players:
        if player.Color is not None:
            username2style[player.Username] = Style(color=player.Color)

    new_text = ''
    backticked = re.finditer(r'`.*?`', text)
    last_stop = 0
    for m in backticked:
        new_text += text[last_stop:m.start()]
        username = m.group(0)[1:-1]
        style = username2style[username]
        new_text += f'[{style}]{username}[/{style}]'
        last_stop = m.end()
    new_text += text[last_stop:]
    return new_text


def _replace_with_style(text: str, replace_str, style) -> str:
    new_text = ''
    last_stop = 0
    for m in re.finditer(replace_str, text):
        new_text += text[last_stop:m.start()]
        new_text += f'[{style}]{m.group(0)}[/{style}]'
        last_stop = m.end()
    new_text += text[last_stop:]
    return new_text
