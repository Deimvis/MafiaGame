# Client

## Launch

Client can be launched using [Dockerfile.client](../Dockerfile.client)

### Arguments

As input argument it takes username

By default Alice will be used as username (see `CMD` command at [Dockerfile.client](../Dockerfile.client))

## API

Client uses RPC methods described at [mafia.proto](../proto/mafia.proto) and _only_ them

## Code

Complete client codebase is stored in the [client](../client) directory
