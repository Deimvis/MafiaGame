import functools
import logging
import random
import threading
from typing import Callable
from collections import defaultdict
from proto import mafia_pb2
from server.server_player import Player
from server.server_vote import Voting
from server.server_events import EventBus
from server.utils.lock import with_RW_lock, read_lock, write_lock
from server.utils.logging import logging_on_call


class UnknownUser(Exception):
    pass


def access(condition: Callable, raise_=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not condition(self, *args, **kwargs):
                if raise_ is not None:
                    raise raise_
                return None
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


is_waiting_for_players = access(lambda self, *args, **kwargs: self.is_waiting_for_players)
is_chat_phase = access(lambda self, *args, **kwargs: self.is_chat_phase)
is_vote_phase = access(lambda self, *args, **kwargs: self.is_vote_phase)
is_night_phase = access(lambda self, *args, **kwargs: self.is_night_phase)
player_is_alive = access(lambda self, *args, **kwargs: self.players[args[0]].is_alive)
player_in_room = access(lambda self, *args, **kwargs: self.has_player(args[0]), raise_=UnknownUser('User is not in the room'))
player_not_in_room = access(lambda self, *args, **kwargs: not self.has_player(args[0]), raise_=RuntimeError('Username is already taken'))
didnt_begin_vote = access(lambda self, *args, **kwargs: not self.begin_vote_info[args[0]])
player_is_mafia = access(lambda self, *args, **kwargs: self.players[args[0]].is_mafia)
player_is_sheriff = access(lambda self, *args, **kwargs: self.players[args[0]].is_sheriff)
suspect_is_alive = access(lambda self, *args, **kwargs: self.players[args[1]].is_alive)
exposed_is_alive = access(lambda self, *args, **kwargs: self.players[args[1]].is_alive)


@with_RW_lock
class Room:
    def __init__(self, game_rules: mafia_pb2.GameRules, *args, **kwargs):
        self._id = str(random.randint(0, 9999)).zfill(4)
        self.day_number = 0
        self.game_rules = game_rules
        self.status = mafia_pb2.Room.RoomStatus.WAITING_FOR_PLAYERS
        self.players = {}  # Dict[str, Player]: username2player
        self.begin_vote_info = None  # Dict[str, bool]: username2begin_vote
        self.voting = None
        self.mafia_voting = None
        self.sheriff_voting = None
        self.chat = None
        self.events = EventBus()
        self.phase_timer = None
        self.exposed = set()
        self._colors = random.sample(['hot_pink', 'plum1', 'dark_orange', 'pale_turquoise1', 'blue', 'green', 'yellow'], self.game_rules.ActivePlayersNumber)  # https://rich.readthedocs.io/en/stable/appendix/colors.html#appendix-colors

    @write_lock
    @is_waiting_for_players
    @player_not_in_room
    @logging_on_call('Add player: {username}', level=logging.INFO)
    def add_player(self, username):
        self.players[username] = Player(username, color=self._colors.pop())
        self.events.user_connected(username, users_connected=len(self.players), total_users=self.game_rules.ActivePlayersNumber)
        if len(self.players) == self.game_rules.ActivePlayersNumber:
            self.start_game()

    @write_lock
    @player_in_room
    @logging_on_call('Remove player: {username}', level=logging.INFO)
    def remove_player(self, username):
        if self.is_waiting_for_players:
            player = self.players.pop(username)
            self._colors.append(player.color)
        self.events.user_disconnected(username, users_connected=len(self.players), total_users=self.game_rules.ActivePlayersNumber)

    @write_lock
    @logging_on_call('Start game', level=logging.INFO)
    def start_game(self):
        self.day_number = 0
        pool = list(self.players.values())
        random.shuffle(pool)
        mafias = []
        for _ in range(self.game_rules.MafiaNumber):
            mafias.append(pool.pop())
        sheriffs = []
        for _ in range(self.game_rules.SheriffNumber):
            sheriffs.append(pool.pop())
        civilians = pool

        for mafia in mafias:
            mafia.set_mafia()
        for sheriff in sheriffs:
            sheriff.set_sheriff()
        for civilian in civilians:
            civilian.set_civilian()

        self.events.roles_set(self.players.values())
        self.begin_new_day()

    @write_lock
    @logging_on_call('Begin new day', level=logging.INFO)
    def begin_new_day(self):
        self.day_number += 1
        self.events.day_began(self.day_number)
        self.start_chat_phase()

    @write_lock
    @logging_on_call('Start chat phase', level=logging.INFO)
    def start_chat_phase(self):
        self.chat = mafia_pb2.Chat(Messages=[])
        self.begin_vote_info = defaultdict(lambda: False)
        self.status = mafia_pb2.Room.RoomStatus.CHAT_PHASE
        self.events.chat_phase_began()

    @write_lock
    @logging_on_call('Start vote phase', level=logging.INFO)
    def start_vote_phase(self):
        self.begin_vote_info = defaultdict(lambda: False)
        self.voting = Voting(self.alive_players, self.alive_players)
        self.status = mafia_pb2.Room.RoomStatus.VOTE_PHASE
        self.events.vote_phase_began()
        self.phase_timer = threading.Timer(60.0, self.finish_vote_phase)
        self.phase_timer.start()

    @write_lock
    @logging_on_call('Finish vote phase', level=logging.INFO)
    def finish_vote_phase(self):
        username_to_kill = self.voting.get_most_voted_username()
        self.players[username_to_kill].kill()
        self.events.player_was_killed(self.players[username_to_kill])
        if self._has_mafia_win_condition():
            self.set_mafia_won()
        elif self._has_mafia_lost_condition():
            self.set_mafia_lost()
        else:
            self.start_night_phase()

    @write_lock
    @logging_on_call('Start night phase', level=logging.INFO)
    def start_night_phase(self):
        self.chat = None
        self.voting = None
        self.mafia_voting = Voting(self.mafia_players, self.alive_players)
        self.sheriff_voting = Voting(self.sheriff_players, self.alive_players)
        self.status = mafia_pb2.Room.RoomStatus.NIGHT_PHASE
        self.events.night_phase_began()
        self.phase_timer = threading.Timer(60.0, self.finish_night_phase)
        self.phase_timer.start()

    @write_lock
    @logging_on_call('Finish night phase', level=logging.INFO)
    def finish_night_phase(self):
        username_to_kill = self.mafia_voting.get_most_voted_username()
        self.players[username_to_kill].kill()
        self.events.player_was_killed(self.players[username_to_kill])
        username_to_expose = self.sheriff_voting.get_most_voted_username()
        self.players[username_to_expose].expose_to(self.sheriff_players.values())
        self.mafia_voting = None
        self.sheriff_voting = None
        if self._has_mafia_win_condition():
            self.set_mafia_won()
        elif self._has_mafia_lost_condition():
            self.set_mafia_lost()
        else:
            self.begin_new_day()

    @write_lock
    @player_in_room
    @player_is_alive
    @logging_on_call('Send message by {username}: {text}', level=logging.INFO)
    def send_message(self, username, text):
        if self.is_chat_phase:
            self.chat.Messages.append(mafia_pb2.Chat.Message(
                AuthorUsername = username,
                Text = text,
            ))
            self.events.global_message_appeared(username, text)
        elif self.is_night_phase:
            player = self.players[username]
            if player.is_mafia:
                self.events.mafia_message_appeared(username, text)
            elif player.is_sheriff:
                self.events.sheriff_message_appeared(username, text)


    @write_lock
    @is_chat_phase
    @player_in_room
    @player_is_alive
    @didnt_begin_vote
    @logging_on_call('Begin vote by {username}', level=logging.INFO)
    def begin_vote(self, username):
        self.begin_vote_info[username] = True
        begin_vote_cnt = self._begin_vote_count()
        alive_players_cnt = self._alive_players_count()
        self.events.player_wants_begin_vote(username, begin_vote_cnt, alive_players_cnt, self.day_number)
        if begin_vote_cnt == alive_players_cnt:
            if self.day_number == 1:
                self.start_night_phase()
            else:
                self.start_vote_phase()

    @write_lock
    @is_vote_phase
    @player_in_room
    @player_is_alive
    @suspect_is_alive
    @logging_on_call('Vote by {username} to {suspect_username}', level=logging.INFO)
    def vote(self, username, suspect_username):
        self.voting.vote(username, suspect_username)
        votes_number = self.voting.get_votes_number(suspect_username)
        self.events.global_vote_appeared(suspect_username, votes_number)
        if self.voting.is_everyone_voted():
            self.phase_timer.cancel()
            self.phase_timer = None
            self.finish_vote_phase()

    @write_lock
    @is_night_phase
    @player_in_room
    @player_is_alive
    @player_is_mafia
    @suspect_is_alive
    @logging_on_call('Vote by mafia {username} to {suspect_username}', level=logging.INFO)
    def mafia_vote(self, username, suspect_username):
        self.mafia_voting.vote(username, suspect_username)
        votes_number = self.mafia_voting.get_votes_number(suspect_username)
        self.events.mafia_vote_appeared(suspect_username, votes_number)
        if self.mafia_voting.is_everyone_voted() and self.sheriff_voting.is_everyone_voted():
            self.phase_timer.cancel()
            self.phase_timer = None
            self.finish_night_phase()

    @write_lock
    @is_night_phase
    @player_in_room
    @player_is_alive
    @player_is_sheriff
    @suspect_is_alive
    @logging_on_call('Vote by sheriff {username} to {suspect_username}', level=logging.INFO)
    def sheriff_vote(self, username, suspect_username):
        self.sheriff_voting.vote(username, suspect_username)
        votes_number = self.sheriff_voting.get_votes_number(suspect_username)
        self.events.sheriff_vote_appeared(suspect_username, votes_number)
        if self.mafia_voting.is_everyone_voted() and self.sheriff_voting.is_everyone_voted():
            self.phase_timer.cancel()
            self.phase_timer = None
            self.finish_night_phase()

    @write_lock
    @player_in_room
    @player_is_alive
    @player_is_sheriff
    @exposed_is_alive
    @logging_on_call('Expose publicly by sheriff {username} to {username_to_expose}', level=logging.INFO)
    def expose(self, username, username_to_expose):
        if username_to_expose in self.exposed:
            return
        self.exposed.add(username_to_expose)
        self.players[username_to_expose].publicly_expose_to(self.players.values())
        self.events.player_was_exposed(username_to_expose)

    @write_lock
    def set_mafia_won(self):
        self.status = mafia_pb2.Room.RoomStatus.MAFIA_WON
        for player in self.players.values():
            player.expose_to(self.players.values())
        self.events.mafia_won()

    @write_lock
    def set_mafia_lost(self):
        self.status = mafia_pb2.Room.RoomStatus.MAFIA_LOST
        for player in self.players.values():
            player.expose_to(self.players.values())
        self.events.mafia_lost()

    @read_lock
    def view(self, username: str) -> mafia_pb2.Room:
        if not self.has_player(username):
            raise UnknownUser('User is not in the room')
        player = self.players[username]
        return mafia_pb2.Room(
            Id = mafia_pb2.Room.RoomId(Value=self._id),
            Status = self.status,
            GameRules = self.game_rules,
            Players = [other_player.view(player) for other_player in self.players.values()],
            Spectators = [],
            Chat = self.chat,
            Voting = self.voting.view(player) if self.voting is not None else None,
            EventBus = self.events.view(player) if self.events is not None else None,
            DayNumber = self.day_number,
        )

    def has_player(self, username):
        return username in self.players

    def _alive_players_count(self):
        count = 0
        for player in self.players.values():
            if player.is_alive:
                count += 1
        return count

    def _begin_vote_count(self):
        count = 0
        for username, wants in self.begin_vote_info.items():
            if wants is True:
                count += 1
        return count

    def _has_mafia_win_condition(self):
        return len(self.mafia_alive_players) >= (len(self.alive_players) + 1) // 2

    def _has_mafia_lost_condition(self):
        return all([not player.is_mafia for player in self.alive_players.values()])

    @property
    def id(self):
        return self._id

    @property
    def is_waiting_for_players(self):
        return self.status == mafia_pb2.Room.RoomStatus.WAITING_FOR_PLAYERS

    @property
    def is_chat_phase(self):
        return self.status == mafia_pb2.Room.RoomStatus.CHAT_PHASE

    @property
    def is_vote_phase(self):
        return self.status == mafia_pb2.Room.RoomStatus.VOTE_PHASE

    @property
    def is_night_phase(self):
        return self.status == mafia_pb2.Room.RoomStatus.NIGHT_PHASE

    @property
    def mafia_players(self):
        return {username: player for username, player in self.players.items() if player.is_mafia}

    @property
    def sheriff_players(self):
        return {username: player for username, player in self.players.items() if player.is_sheriff}

    @property
    def alive_players(self):
        return {username: player for username, player in self.players.items() if player.is_alive}

    @property
    def mafia_alive_players(self):
        return {username: player for username, player in self.players.items() if player.is_mafia and player.is_alive}
