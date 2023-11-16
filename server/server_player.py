import logging
from typing import Iterable
from proto import mafia_pb2


class Player:
    def __init__(self, username, color=None):
        self._username = username
        self.role = mafia_pb2.Player.PlayerRole.PR_UNKNOWN
        self.status = mafia_pb2.Player.PlayerStatus.PS_UNKNOWN
        self.color = color
        self.exposed = False
        self._known_players = {username}

    @property
    def is_civilian(self):
        return self.role == mafia_pb2.Player.PlayerRole.PR_CIVILIAN

    @property
    def is_mafia(self):
        return self.role == mafia_pb2.Player.PlayerRole.PR_MAFIA

    @property
    def is_sheriff(self):
        return self.role == mafia_pb2.Player.PlayerRole.PR_SHERIFF

    @property
    def is_alive(self):
        return self.status == mafia_pb2.Player.PlayerStatus.PS_ALIVE

    @property
    def is_dead(self):
        return self.status == mafia_pb2.Player.PlayerStatus.PS_DEAD

    def set_civilian(self):
        self.role = mafia_pb2.Player.PlayerRole.PR_CIVILIAN
        self.status = mafia_pb2.Player.PlayerStatus.PS_ALIVE

    def set_mafia(self):
        self.role = mafia_pb2.Player.PlayerRole.PR_MAFIA
        self.status = mafia_pb2.Player.PlayerStatus.PS_ALIVE

    def set_sheriff(self):
        self.role = mafia_pb2.Player.PlayerRole.PR_SHERIFF
        self.status = mafia_pb2.Player.PlayerStatus.PS_ALIVE

    def add_to_known(self, other: 'Player'):
        self._known_players.add(other.username)

    def kill(self):
        logging.info(f'Kill {self.username}')
        self.status = mafia_pb2.Player.PlayerStatus.PS_DEAD

    def expose_to(self, other_players: Iterable['Player']):
        for other_player in other_players:
            other_player.add_to_known(self)

    def publicly_expose_to(self, other_players: Iterable['Player']):
        self.exposed = True
        for other_player in other_players:
            other_player.add_to_known(self)

    def know_about(self, other: 'Player'):
        if self.is_dead:
            return True
        if other.is_dead:
            return True
        if self.is_mafia and other.is_mafia:
            return True
        if self.is_sheriff and other.is_sheriff:
            return True
        return other.username in self._known_players

    def view(self, other: 'Player'):
        if other.know_about(self):
            return mafia_pb2.Player(
                Username=self.username,
                Role=self.role,
                Status=self.status,
                Color=self.color,
                Exposed=self.exposed,
            )
        else:
            return mafia_pb2.Player(
                Username=self.username,
                Role=mafia_pb2.Player.PlayerRole.PR_UNKNOWN,
                Status=self.status,
                Color=self.color,
                Exposed=self.exposed,
            )

    @property
    def username(self):
        return self._username
