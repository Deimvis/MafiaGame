import asyncpg
import os


INIT_DB_SCRIPT = '''
CREATE TABLE IF NOT EXISTS "user" (
    username VARCHAR(512) PRIMARY KEY,
    avatar bytea,
    sex VARCHAR(32),
    email VARCHAR(2048)
);
'''


async def init_db(pool):
    async with pool.acquire() as con:
        await con.execute(INIT_DB_SCRIPT)

async def create_pool():
    return await asyncpg.create_pool(
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        database=os.getenv('POSTGRES_DB'),
        host=os.getenv('POSTGRES_HOST'),
        port=int(os.getenv('POSTGRES_PORT', '5432')),
    )
