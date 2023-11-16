
from typing import Dict
from proto import mafia_pb2
from server.server_player import Player


class Voting:
    def __init__(self, players: Dict[str, Player], suspects: Dict[str, Player]):
        self.voting = {username: None for username in players}
        self.suspects = {username: 0 for username in suspects}

    def vote(self, username, suspect_username):
        prev_suspect = self.voting[username]
        self.voting[username] = suspect_username
        if prev_suspect is not None:
            self.suspects[prev_suspect] -= 1
        self.suspects[suspect_username] += 1

    def get_votes_number(self, suspect_username):
        return self.suspects[suspect_username]

    def get_most_voted_username(self):
        return max(self.suspects, key=self.suspects.get)

    def is_everyone_voted(self):
        return all([vote is not None for vote in self.voting.values()])

    def view(self, player: Player) -> mafia_pb2.Voting:
        votes = []
        for suspect_username, votes_number in self.suspects.items():
            vote = mafia_pb2.Voting.Vote(
                SuspectUsername = suspect_username,
                VotesNumber = votes_number,
            )
            votes.append(vote)
        return mafia_pb2.Voting(Votes=votes)
