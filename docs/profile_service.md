# Profile service

## Launch

Will be launched together with the server, but can be manually launched with
```bash
docker-compose run --rm -p 8000:8000 profile_service
```

## API

Full OpenAPI specification can be found at `localhost:8000/docs` after launch or in [openapi.json](../services/profile/openapi.json)

### /user
* `POST` — Create user
  * Body: [User](#user)

### /user/{username: string}
* `GET` — Get user
* `PUT` — Update user
  * Body: [User](#user)
* `DELETE` — Delete user

### /user/{username: string}/avatar
* `POST` — Upload avatar
  * Body: Image data

### /users
* `POST` — Get users
  * Body: List[username]

## Models

### User
* username: string
* avatar: string (optional)
* sex: string (optional)
* email: string (otional)

_use [`POST` /user/{username: string}/avatar](#userusername-stringavatar) for uploading avatar in binary format_
