from pydantic import BaseModel
from proto import mafia_pb2


class Config(BaseModel):
    host: str
    port: int
    active_players_number: int
    mafia_number: int
    sheriff_number: int

    def game_rules(self) -> mafia_pb2.GameRules:
        return mafia_pb2.GameRules(
            ActivePlayersNumber=self.active_players_number,
            MafiaNumber=self.mafia_number,
            SheriffNumber=self.sheriff_number
        )
