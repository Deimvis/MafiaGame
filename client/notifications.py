import time
from client.console import global_console
from client.shared_data import get_room_info
from proto import mafia_pb2


class NotificationsView:
    def __init__(self, client, prompts_manager):
        self.client = client
        self.prompts_manager = prompts_manager
        self.last_seen_event_index = None

    def poll(self, stop=lambda: False):
        while not stop():
            room_info = get_room_info()
            events = room_info.EventBus.Events
            if len(events) > 0:
                if self.last_seen_event_index is not None:
                    new_events_count = events[-1].Index - self.last_seen_event_index
                else:
                    new_events_count = len(events)
                if new_events_count > 0:
                    for ind in range(len(events) - new_events_count, len(events)):
                        self.handle_event(events[ind])
                    self.last_seen_event_index = events[-1].Index
            time.sleep(0.5)

    def handle_event(self, event: mafia_pb2.EventBus.Event):
        with global_console as console:
            prefix = '> '
            if 'phase' in event.Message and not 'wants to finish' in event.Message:
                prefix = '>> '
            if 'DAY' in event.Message:
                prefix = '>>> '
            console.print(prefix + event.Message)
        if self.client.is_alive:
            match event.Message.strip():
                case 'Day phase: chat':
                    if len(self.client.get_expose_options()) > 0:
                        self.prompts_manager.set_sheriff_expose_prompt()
                    else:
                        self.prompts_manager.set_chat_phase_prompt()
                case 'Day phase finished: vote for mafia (60 seconds)':
                    self.prompts_manager.set_vote_phase_prompt()
                case 'Night phase: mafia choose victim, sheriffs investigate people (60 seconds)':
                    if self.client.is_mafia:
                        self.prompts_manager.set_mafia_night_prompt()
                    if self.client.is_sheriff:
                        self.prompts_manager.set_sheriff_night_prompt()
