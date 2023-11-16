import random
from collections import deque
from server.server_player import Player
from typing import Callable, Iterable
from proto import mafia_pb2


class EventBus:
    def __init__(self, max_size=100):
        self.max_size = max_size
        self.events = deque()
        self.next_event_index = 0

    def add_event(self, msg, access: Callable[[Player], bool] = lambda player: True):
        if len(self.events) == self.max_size:
            self.events.popleft()
        self.events.append((self.next_event_index, msg, access))
        self.next_event_index += 1

    def user_connected(self, username, users_connected: int, total_users: int):
        self.add_event(f'Player `{username}` conntected: {users_connected}/{total_users}')

    def user_disconnected(self, username, users_connected: int, total_users: int):
        self.add_event(f'Player `{username}` disconnected: {users_connected}/{total_users}')

    def roles_set(self, players: Iterable[Player]):
        for player in players:
            self.add_event(f'You got role {_beautify_role(player.role)}', access=lambda p, player=player: p.username == player.username)

    def day_began(self, day_number):
        self.add_event(f'DAY {day_number}')

    def chat_phase_began(self):
        self.add_event('Day phase: chat')

    def vote_phase_began(self):
        self.add_event('Day phase finished: vote for mafia (60 seconds)')

    def night_phase_began(self):
        self.add_event('Night phase: mafia choose victim, sheriffs investigate people (60 seconds)')

    def global_message_appeared(self, username, text):
        self.add_event(f'`{username}`: {text}')

    def mafia_message_appeared(self, username, text):
        self.add_event(f'`{username}`: {text}', access=lambda p: p.is_mafia)

    def sheriff_message_appeared(self, username, text):
        self.add_event(f'`{username}`: {text}', access=lambda p: p.is_sheriff)

    def player_wants_begin_vote(self, username, begin_vote_cnt, alive_players_cnt, day_number):
        if day_number == 1:
            self.add_event(f'`{username}` wants to finish day phase: {begin_vote_cnt}/{alive_players_cnt}')
        else:
            self.add_event(f'`{username}` wants to finish day phase and begin vote: {begin_vote_cnt}/{alive_players_cnt}')

    def global_vote_appeared(self, suspect_username, votes_number):
        self.add_event(f'Votes for `{suspect_username}`: {votes_number}')

    def mafia_vote_appeared(self, suspect_username, votes_number):
        self.add_event(f'Votes for `{suspect_username}`: {votes_number}', access=lambda p: p.is_mafia)

    def sheriff_vote_appeared(self, suspect_username, votes_number):
        self.add_event(f'Votes for `{suspect_username}`: {votes_number}', access=lambda p: p.is_sheriff)

    def player_was_killed(self, killed_player: Player):
        self.add_event(f'Player was killed: `{killed_player.username}` ({_beautify_role(killed_player.role)})')

    def player_was_exposed_to_sheriffs(self, username):
        self.add_event(f'Player was exposed to sheriffs: `{username}`. Now you expose him publicly')

    def player_was_exposed(self, username):
        self.add_event(f'Player was exposed: `{username}`')

    def mafia_won(self):
        self.add_event('Mafia WON!')

    def mafia_lost(self):
        self.add_event('Mafia LOST!')

    def view(self, player: Player) -> mafia_pb2.EventBus:
        accessed_events = []
        for event_index, event_msg, event_access in self.events:
            if event_access(player):
                accessed_events.append(mafia_pb2.EventBus.Event(Index=event_index, Message=event_msg))
        return mafia_pb2.EventBus(
            Events=accessed_events,
        )


def _beautify_role(player_role: int):
    conversion = {
        mafia_pb2.Player.PlayerRole.PR_UNKNOWN: '???',
        mafia_pb2.Player.PlayerRole.PR_CIVILIAN: 'Civilian',
        mafia_pb2.Player.PlayerRole.PR_MAFIA: 'Mafia',
        mafia_pb2.Player.PlayerRole.PR_SHERIFF: 'Sheriff',
    }
    return conversion[player_role]
