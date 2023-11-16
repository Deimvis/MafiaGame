import sys
from abc import ABC, abstractmethod
from typing import List
from PyInquirer import prompt
from client.shared_data import get_room_info, set_current_prompt
from proto import mafia_pb2


class PromptBase(ABC):
    def __init__(self, id, client, prompts_manager):
        self.id = id
        self.client = client
        self.prompts_manager = prompts_manager

    @abstractmethod
    def show(self, console) -> None:
        pass

    @property
    @abstractmethod
    def questions(self) -> List:
        pass

    def __eq__(self, other: 'PromptBase') -> bool:
        return self.id == other.id


class MainMenuPrompt(PromptBase):
    def show(self, console):
        answers = prompt(self.questions)
        if 'main_menu' not in answers:
            return
        match answers['main_menu']:
            case 'Continue':
                return
            case 'Players':
                room_info = get_room_info()
                console.print(f'{len(room_info.Players)}/{room_info.GameRules.ActivePlayersNumber}')
                for player in room_info.Players:
                    suffix = ''
                    if player.Exposed:
                        suffix = ' [EXPOSED]'
                    if player.Status == mafia_pb2.Player.PlayerStatus.PS_DEAD:
                        suffix = ' [DEAD]'
                    console.print(f'{player.Username} ({_beautify_role(player.Role)})' + suffix)
            case 'Game rules':
                room_info = get_room_info()
                game_rules = room_info.GameRules
                console.print(f'Players: {game_rules.ActivePlayersNumber}')
                console.print(f'Mafia: {game_rules.MafiaNumber}')
                console.print(f'Sheriff: {game_rules.SheriffNumber}')
            case 'Disconnect':
                self.client.disconnect()
                console.print('Disconnected', style='red')
                sys.exit()
            case 'Write message':
                message = input('Write message: ')
                self.client.send_message(message)
            case 'Finish day phase':
                self.client.begin_vote()
            case 'Vote for mafia':
                self.prompts_manager.set_vote_phase_prompt()
            case 'Choose victim':
                self.prompts_manager.set_mafia_vote_prompt()
            case 'Write message to mafia chat':
                message = input('Write message: ')
                self.client.send_message(message)
            case 'Choose player to expose':
                self.prompts_manager.set_sheriff_vote_prompt()
            case 'Write message to sheriffs chat':
                message = input('Write message: ')
                self.client.send_message(message)
            case 'Expose player':
                self.prompts_manager.set_sheriff_expose_prompt()

    @property
    def questions(self) -> List:
        choices = [
            'Continue',
            'Players',
            'Game rules',
            'Disconnect',
        ]
        if self.client.is_alive:
            room_info = get_room_info()
            match room_info.Status:
                case mafia_pb2.Room.RoomStatus.CHAT_PHASE:
                    choices.insert(1, 'Write message')
                    choices.insert(2, 'Finish day phase')
                    if len(self.client.get_expose_options()) > 0:
                        choices.insert(1, 'Expose player')
                case mafia_pb2.Room.RoomStatus.VOTE_PHASE:
                    choices.insert(1, 'Vote for mafia')
                case mafia_pb2.Room.RoomStatus.NIGHT_PHASE:
                    if self.client.is_mafia:
                        choices.insert(1, 'Choose victim')
                        choices.insert(2, 'Write message to mafia chat')
                    if self.client.is_sheriff:
                        choices.insert(1, 'Choose player to expose')
                        choices.insert(2, 'Write message to sheriffs chat')
        return [
            {
                'type': 'list',
                'name': 'main_menu',
                'message': 'Menu',
                'choices': choices
            }
        ]


class ChatPhasePrompt(PromptBase):
    def show(self, console):
        answers = prompt(self.questions)
        if 'chat_phase_menu' not in answers:
            return
        match answers['chat_phase_menu']:
            case 'Open chat':
                return
            case 'Write message':
                message = input('Write message: ')
                self.client.send_message(message)
            case 'Finish day phase':
                self.client.begin_vote()

    @property
    def questions(self) -> List:
        return [
            {
                'type': 'list',
                'name': 'chat_phase_menu',
                'message': 'Chat Phase',
                'choices': [
                    'Open chat',
                    'Write message',
                    'Finish day phase',
                ]
            }
        ]


class VotePhasePrompt(PromptBase):
    def show(self, console):
        answers = prompt(self.questions)
        if 'vote_phase_prompt' not in answers:
            return
        suspect_username = answers['vote_phase_prompt']
        self.client.vote(suspect_username)

    @property
    def questions(self) -> List:
        choices = []
        room_info = get_room_info()
        for player in room_info.Players:
            if (player.Username != self.client.username
                    and player.Status == mafia_pb2.Player.PlayerStatus.PS_ALIVE):
                choices.append(player.Username)
        return [
            {
                'type': 'list',
                'name': 'vote_phase_prompt',
                'message': 'Vote for mafia',
                'choices': choices,
            },
        ]


class MafiaNightPrompt(PromptBase):
    def show(self, console):
        answers = prompt(self.questions)
        if 'mafia_night_menu' not in answers:
            return
        match answers['mafia_night_menu']:
            case 'Choose victim':
                self.prompts_manager.set_mafia_vote_prompt()
            case 'Open mafia chat':
                return
            case 'Write message to mafia chat':
                message = input('Write message: ')
                self.client.send_message(message)

    @property
    def questions(self) -> List:
        return [
            {
                'type': 'list',
                'name': 'mafia_night_menu',
                'message': 'Night phase',
                'choices': [
                    'Choose victim',
                    'Open mafia chat',
                    'Write message to mafia chat',
                ]
            },
        ]


class MafiaVotePrompt(PromptBase):
    def show(self, console):
        answers = prompt(self.questions)
        if 'mafia_vote_menu' not in answers:
            return
        suspect_username = answers['mafia_vote_menu']
        self.client.mafia_vote(suspect_username)

    @property
    def questions(self) -> List:
        choices = []
        room_info = get_room_info()
        for player in room_info.Players:
            if (player.Username != self.client.username
                    and player.Status == mafia_pb2.Player.PlayerStatus.PS_ALIVE):
                choices.append(player.Username)
        return [
            {
                'type': 'list',
                'name': 'mafia_vote_menu',
                'message': 'Choose whom to kill',
                'choices': choices
            },
        ]


class SheriffNightPrompt(PromptBase):
    def show(self, console):
        answers = prompt(self.questions)
        if 'sheriff_night_menu' not in answers:
            return
        match answers['sheriff_night_menu']:
            case 'Choose player to expose':
                self.prompts_manager.set_sheriff_vote_prompt()
            case 'Open sheriffs chat':
                return
            case 'Write message to sheriffs chat':
                message = input('Write message: ')
                self.client.send_message(message)

    @property
    def questions(self) -> List:
        return [
            {
                'type': 'list',
                'name': 'sheriff_night_menu',
                'message': 'Night phase',
                'choices': [
                    'Choose player to expose',
                    'Open sheriffs chat',
                    'Write message to sheriffs chat',
                ]
            },
        ]


class SheriffVotePrompt(PromptBase):
    def show(self, console):
        answers = prompt(self.questions)
        if 'sheriff_vote_menu' not in answers:
            return
        suspect_username = answers['sheriff_vote_menu']
        self.client.sheriff_vote(suspect_username)

    @property
    def questions(self) -> List:
        choices = []
        room_info = get_room_info()
        for player in room_info.Players:
            if (player.Username != self.client.username
                    and player.Status == mafia_pb2.Player.PlayerStatus.PS_ALIVE
                    and not player.Exposed):
                choices.append(player.Username)
        return [
            {
                'type': 'list',
                'name': 'sheriff_vote_menu',
                'message': 'Choose whom to expose',
                'choices': choices
            },
        ]


class SheriffExposePrompt(PromptBase):
    def show(self, console):
        answers = prompt(self.questions)
        if 'sheriff_expose_menu' not in answers:
            return
        username_to_expose = answers['sheriff_expose_menu']
        self.client.expose(username_to_expose)

    @property
    def questions(self) -> List:
        return [
            {
                'type': 'list',
                'name': 'sheriff_expose_menu',
                'message': 'You can expose any of those player publicly',
                'choices': self.client.get_expose_options()
            },
        ]


class PromptsManager():
    def __init__(self, client):
        self.client = client
        self.next_prompt_id = 0

    def get_main_menu(self) -> MainMenuPrompt:
        p = MainMenuPrompt(self.next_prompt_id, self.client, self)
        self.next_prompt_id += 1
        return p

    def set_chat_phase_prompt(self) -> None:
        p = ChatPhasePrompt(self.next_prompt_id, self.client, self)
        self.next_prompt_id += 1
        set_current_prompt(p)

    def set_vote_phase_prompt(self) -> None:
        p = VotePhasePrompt(self.next_prompt_id, self.client, self)
        self.next_prompt_id += 1
        set_current_prompt(p)

    def set_mafia_night_prompt(self) -> None:
        p = MafiaNightPrompt(self.next_prompt_id, self.client, self)
        self.next_prompt_id += 1
        set_current_prompt(p)

    def set_sheriff_night_prompt(self) -> None:
        p = SheriffNightPrompt(self.next_prompt_id, self.client, self)
        self.next_prompt_id += 1
        set_current_prompt(p)

    def set_mafia_vote_prompt(self) -> None:
        p = MafiaVotePrompt(self.next_prompt_id, self.client, self)
        self.next_prompt_id += 1
        set_current_prompt(p)

    def set_sheriff_vote_prompt(self) -> None:
        p = SheriffVotePrompt(self.next_prompt_id, self.client, self)
        self.next_prompt_id += 1
        set_current_prompt(p)

    def set_sheriff_expose_prompt(self) -> None:
        p = SheriffExposePrompt(self.next_prompt_id, self.client, self)
        self.next_prompt_id += 1
        set_current_prompt(p)


def _beautify_role(player_role: int):
    conversion = {
        mafia_pb2.Player.PlayerRole.PR_UNKNOWN: '???',
        mafia_pb2.Player.PlayerRole.PR_CIVILIAN: 'Civilian',
        mafia_pb2.Player.PlayerRole.PR_MAFIA: 'Mafia',
        mafia_pb2.Player.PlayerRole.PR_SHERIFF: 'Sheriff',
    }
    return conversion[player_role]
