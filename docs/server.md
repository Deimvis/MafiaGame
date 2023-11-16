# Server

## Launch

Server can be launched using [Dockerfile.server](../Dockerfile.server)

### Arguments

As input argument it takes path to config file which scheme defined at [config.py](../server/config.py)

By default [default.json](../server/configs/default.json) will be used as a config

## API

Server supports all RPC methods described at [mafia.proto](../proto/mafia.proto)

## Code

Complete server codebase is stored in [server](../server) directory
