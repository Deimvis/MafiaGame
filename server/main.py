import argparse
import logging
from server.config import Config
from server.run_server import start_server


logging.basicConfig(level=logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(description='Mafia coordination server')
    parser.add_argument('config', type=str, help='Path to server config')
    return parser.parse_args()


def main():
    args = parse_args()
    config = Config.parse_file(args.config)
    logging.info(f'Use config:\n{config.json(indent=4)}')
    start_server(config)


if __name__ == '__main__':
    main()
