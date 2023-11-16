import argparse
import grpc
from proto import mafia_pb2_grpc
from client.run_client import start_client


def parse_args():
    parser = argparse.ArgumentParser(description='Mafia client')
    parser.add_argument('--username', type=str)
    parser.add_argument('--server-host', type=str)
    parser.add_argument('--server-port', type=int)
    return parser.parse_args()


def main():
    args = parse_args()
    with grpc.insecure_channel(f'{args.server_host}:{args.server_port}') as channel:
        stub = mafia_pb2_grpc.CoordinatorStub(channel)
        start_client(stub, args.username)


if __name__ == '__main__':
    main()
