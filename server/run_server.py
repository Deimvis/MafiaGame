import grpc
import logging
import time
import traceback
from concurrent import futures
from google.protobuf import empty_pb2
from server.config import Config
from server.server_room import Room, UnknownUser
from proto import (
    mafia_pb2_grpc,
    mafia_pb2,
)


class CoordinatorService(mafia_pb2_grpc.CoordinatorServicer):
    def __init__(self, config: Config):
        self.config = config
        self.room = Room(config.game_rules())

    def Connect(self, request: mafia_pb2.User, context):
        try:
            self.room.add_player(request.Username)
            prev_room_pb = None
            while True:
                room_pb = self.room.view(request.Username)
                if room_pb != prev_room_pb:
                    yield room_pb
                    prev_room_pb = room_pb
                else:
                    time.sleep(0.5)
        except UnknownUser:
            return
        except Exception as error:
            msg = f'Got error during Connect:\nError: {error}\nTraceback: {traceback.format_exc()}'
            logging.error(msg)
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, msg)

    def Disconnect(self, request: mafia_pb2.DisconnectRequest, context):
        if request.RoomId.Value != self.room.id:
            logging.debug(f'User {request.User.Username} tries to disconnect from incorrect room {request.RoomId.Value}')
            return empty_pb2.Empty()
        try:
            self.room.remove_player(request.User.Username)
            return empty_pb2.Empty()
        except UnknownUser:
            return empty_pb2.Empty()
        except Exception as error:
            msg = f'Got error during Disconnect:\nError: {error}\nTraceback: {traceback.format_exc()}'
            logging.error(msg)
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, msg)

    def SendMessage(self, request: mafia_pb2.Chat.Message, context):
        try:
            self.room.send_message(request.AuthorUsername, request.Text)
            return empty_pb2.Empty()
        except Exception as error:
            msg = f'Got error during SendMessage:\nError: {error}\nTraceback: {traceback.format_exc()}'
            logging.error(msg)
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, msg)

    def BeginVote(self, request: mafia_pb2.User, context):
        try:
            self.room.begin_vote(request.Username)
            return empty_pb2.Empty()
        except Exception as error:
            msg = f'Got error during BeginVote:\nError: {error}\nTraceback: {traceback.format_exc()}'
            logging.error(msg)
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, msg)

    def Vote(self, request: mafia_pb2.VoteRequest, context):
        try:
            self.room.vote(request.User.Username, request.SuspectUser.Username)
            return empty_pb2.Empty()
        except Exception as error:
            msg = f'Got error during BeginVote:\nError: {error}\nTraceback: {traceback.format_exc()}'
            logging.error(msg)
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, msg)

    def MafiaVote(self, request: mafia_pb2.VoteRequest, context):
        try:
            self.room.mafia_vote(request.User.Username, request.SuspectUser.Username)
            return empty_pb2.Empty()
        except Exception as error:
            msg = f'Got error during BeginVote:\nError: {error}\nTraceback: {traceback.format_exc()}'
            logging.error(msg)
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, msg)

    def SheriffVote(self, request: mafia_pb2.VoteRequest, context):
        try:
            self.room.sheriff_vote(request.User.Username, request.SuspectUser.Username)
            return empty_pb2.Empty()
        except Exception as error:
            msg = f'Got error during BeginVote:\nError: {error}\nTraceback: {traceback.format_exc()}'
            logging.error(msg)
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, msg)

    def Expose(self, request: mafia_pb2.ExposeRequest, context):
        try:
            self.room.expose(request.User.Username, request.UserToExpose.Username)
            return empty_pb2.Empty()
        except Exception as error:
            msg = f'Got error during BeginVote:\nError: {error}\nTraceback: {traceback.format_exc()}'
            logging.error(msg)
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, msg)


def make_server(config):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    mafia_pb2_grpc.add_CoordinatorServicer_to_server(CoordinatorService(config), server)
    server.add_insecure_port(f'{config.host}:{config.port}')
    return server


def poll(server):
    server.start()
    server.wait_for_termination()


def start_server(config: Config):
    server = make_server(config)
    poll(server)
