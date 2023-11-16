from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import List

from . import (
    db,
    models,
)


app = FastAPI()


@app.on_event('startup')
async def startup():
    app.db_pool = await db.create_pool()
    await db.init_db(app.db_pool)

@app.on_event('shutdown')
async def shutdown():
    await app.db_pool.close()

@app.get('/')
async def index() -> str:
    return 'Profile Service'

@app.get('/user/{username}')
async def get_user(username: str) -> models.User | None:
    query = 'SELECT username, avatar, sex, email FROM "user" WHERE username = $1;'
    record = await app.db_pool.fetchrow(query, username)
    if record is None:
        return HTTPException(404, 'No such user exists')
    return models.User(
        username=record['username'],
        avatar=record['avatar'],
        sex=record['sex'],
        email=record['email'],
    )

@app.post('/users')
async def get_users(usernames: List[str]) -> List[models.User]:
    return [models.User(username='my_user')]

@app.post('/user')
async def create_user(user: models.User) -> JSONResponse:
    query = 'INSERT INTO "user" (username, avatar, sex, email) VALUES ($1, $2, $3, $4);'
    await app.db_pool.execute(query, user.username, user.avatar, user.sex, user.email)
    return JSONResponse(status_code=200, content={'status': f'User `{user.username}` created'})

@app.put('/user/{username}')
async def update_user(user: models.User) -> JSONResponse:
    if not await is_user_exists(user.username):
        return HTTPException(404, 'No such user exists')
    query = 'UPDATE "user" SET username = $1, avatar = $2, sex = $3, email = $4 WHERE username = $1;'
    await app.db_pool.execute(query, user.username, user.avatar, user.sex, user.email)
    return JSONResponse(status_code=200, content={'status': f'User `{user.username}` updated'})

@app.delete('/user/{username}')
async def delete_user(username: str) -> JSONResponse:
    if not await is_user_exists(username):
        return HTTPException(404, 'No such user exists')
    query = 'DELETE FROM "user" WHERE username = $1;'
    await app.db_pool.execute(query, username)
    return JSONResponse(status_code=200, content={'status': f'User `{username}` deleted'})

@app.post('/user/{username}/avatar')
async def upload_avatar(username: str, request: Request) -> JSONResponse:
    if not await is_user_exists(username):
        return HTTPException(404, 'No such user exists')
    data = await request.body()
    query = 'UPDATE "user" SET avatar = $1 WHERE username = $2;'
    record = await app.db_pool.execute(query, data, username)
    return JSONResponse(status_code=200, content={'status': f'Avatar uploaded for `{username}`'})


async def is_user_exists(username) -> bool:
    query = 'SELECT username FROM "user" WHERE username = $1'
    record = await app.db_pool.fetchrow(query, username)
    return record is not None
