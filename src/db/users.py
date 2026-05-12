import asyncpg
from src.config import settings

async def get_conn():
    # The schema is defined by the search_path in the connection string
    return await asyncpg.connect(settings.DATABASE_URL)

async def get_user_by_username(username: str):
    conn = await get_conn()
    # Assuming the table is named 'users' and is in the 'Agent' schema
    # The search_path in the DATABASE_URL should be set to 'Agent'
    user = await conn.fetchrow('SELECT * FROM "Agent"."users" WHERE username = $1', username)
    await conn.close()
    return user
