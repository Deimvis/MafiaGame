import functools
import grpc
import logging
import sys
import time
import threading
import traceback
from typing import List
from client.console import global_console
from client.shared_data import get_current_prompt, get_room_info, poll_room_info
from client.notifications import NotificationsView
from client.prompts import PromptsManager
from proto import mafia_pb2


class Client:
    def __init__(self, stub, username):
        self.stub = stub
        self.username = username
        self.disconnected = False
        self.threads = []
        self.prompts_manager = PromptsManager(self)
        self.prev_prompt = None

    def start(self):
        self.connect()
        self.show_notifications()
        self.handle_input()

    def connect(self):
        connection_response = try_(n_times=3, sleep_time_s=10)(self.stub.Connect)(mafia_pb2.User(Username=self.username))
        connection_thread = threading.Thread(target=poll_room_info, args=(connection_response,), kwargs={'stop': lambda: self.disconnected is True})
        connection_thread.start()
        self.threads.append(connection_thread)
        while get_room_info() is None:
            if not connection_thread.is_alive():
                with global_console as console:
                    console.print('Can\'t connect to server (maybe username is already taken)', style='red')
                sys.exit(1)
            time.sleep(0.1)

    def show_notifications(self):
        notifications_view = NotificationsView(self, self.prompts_manager)
        notifications_thread = threading.Thread(target=notifications_view.poll, kwargs={'stop': lambda: self.disconnected is True})
        notifications_thread.start()
        self.threads.append(notifications_thread)

    def handle_input(self):
        with global_console as console:
            console.print('Ctrl+C to open menu', style='red')
        while True:
            try:
                self._handle_input()
            except KeyboardInterrupt:
                self.show_main_menu()
            except Exception as error:
                logging.error(f'Got exception!\nError: {error}\nTraceback: {traceback.format_exc()}')
                self.stop()

    def _handle_input(self):
        while True:
            if self._got_error():
                self.stop()

            current_prompt = get_current_prompt()
            if current_prompt is None or (self.prev_prompt is not None and current_prompt == self.prev_prompt):
                time.sleep(1)
                continue
            with global_console as console:
                current_prompt.show(console)
            self.prev_prompt = current_prompt

    def show_main_menu(self):
        try:
            main_menu_prompt = self.prompts_manager.get_main_menu()
            with global_console as console:
                main_menu_prompt.show(console)
        except Exception as error:
            logging.error(f'Got exception!\nError: {error}\nTraceback: {traceback.format_exc()}')
            self.stop()

    def _got_error(self) -> bool:
        for thr in self.threads:
            if not thr.is_alive():
                return True
        return False

    def send_message(self, message: str):
        try:
            self.stub.SendMessage(mafia_pb2.Chat.Message(
                AuthorUsername = self.username,
                Text = message,
            ))
        except Exception as error:
            logging.error(f'Got error during send message: {error}')

    def begin_vote(self):
        try:
            self.stub.BeginVote(mafia_pb2.User(Username=self.username))
        except Exception as error:
            logging.error(f'Got error during begin vote: {error}')

    def vote(self, suspect_username):
        try:
            self.stub.Vote(mafia_pb2.VoteRequest(
                User = mafia_pb2.User(Username=self.username),
                SuspectUser = mafia_pb2.User(Username=suspect_username),
            ))
        except Exception as error:
            logging.error(f'Got error during vote: {error}')

    def mafia_vote(self, suspect_username):
        try:
            self.stub.MafiaVote(mafia_pb2.VoteRequest(
                User = mafia_pb2.User(Username=self.username),
                SuspectUser = mafia_pb2.User(Username=suspect_username),
            ))
        except Exception as error:
            logging.error(f'Got error during mafia vote: {error}')

    def sheriff_vote(self, suspect_username):
        try:
            self.stub.SheriffVote(mafia_pb2.VoteRequest(
                User = mafia_pb2.User(Username=self.username),
                SuspectUser = mafia_pb2.User(Username=suspect_username),
            ))
        except Exception as error:
            logging.error(f'Got error during sheriff vote: {error}')

    def expose(self, username_to_expose):
        try:
            self.stub.Expose(mafia_pb2.ExposeRequest(
                User = mafia_pb2.User(Username=self.username),
                UserToExpose = mafia_pb2.User(Username=username_to_expose),
            ))
        except Exception as error:
            logging.error(f'Got error during expose: {error}')

    def disconnect(self):
        try:
            room_info = get_room_info()
            if room_info is not None:
                self.stub.Disconnect(mafia_pb2.DisconnectRequest(
                    User = mafia_pb2.User(Username=self.username),
                    RoomId = mafia_pb2.Room.RoomId(Value=room_info.Id.Value),
                ))
        except grpc.RpcError:
            pass
        except Exception as error:
            logging.error(f'Got error during disconnect: {error}')
        self.disconnected = True
        for thr in self.threads:
            if thr.is_alive():
                thr.join()

    def stop(self):
        self.disconnect()
        sys.exit(1)

    @property
    def me(self) -> mafia_pb2.Player | None:
        room_info = get_room_info()
        me = None
        for player in room_info.Players:
            if player.Username == self.username:
                me = player
        return me

    @property
    def is_alive(self):
        me = self.me
        return me is not None and me.Status == mafia_pb2.Player.PlayerStatus.PS_ALIVE

    @property
    def is_mafia(self):
        me = self.me
        return me is not None and me.Role == mafia_pb2.Player.PlayerRole.PR_MAFIA

    @property
    def is_sheriff(self):
        me = self.me
        return me is not None and me.Role == mafia_pb2.Player.PlayerRole.PR_SHERIFF

    def get_expose_options(self) -> List[str]:
        if not self.is_sheriff:
            return []
        options = []
        room_info = get_room_info()
        for player in room_info.Players:
            if (player.Username != self.username
                    and player.Status == mafia_pb2.Player.PlayerStatus.PS_ALIVE
                    and player.Role != mafia_pb2.Player.PlayerRole.PR_UNKNOWN
                    and not player.Exposed):
                options.append(player.Username)
        return options


def start_client(stub, username):
    client = Client(stub, username)
    client.start()


def try_(n_times, sleep_time_s):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for try_number in range(1, n_times + 1):
                try:
                    return func(*args, **kwargs)
                except:
                    if try_number == n_times:
                        raise
                    time.sleep(sleep_time_s)
        return wrapper
    return decorator
