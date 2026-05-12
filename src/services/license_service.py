import asyncpg
from src.config import settings
from src.models.license import License
import uuid

async def get_conn():
    return await asyncpg.connect(settings.DATABASE_URL)

async def create_license(user_id: str, agent_id: str) -> License:
    conn = await get_conn()
    license_key = str(uuid.uuid4())
    new_license_data = await conn.fetchrow(
        'INSERT INTO "Agent".licenses (user_id, agent_id, license_key) VALUES ($1, $2, $3) RETURNING *',
        user_id, agent_id, license_key
    )
    await conn.close()
    return License(**new_license_data)

async def get_license_by_key(license_key: str) -> License | None:
    conn = await get_conn()
    license_data = await conn.fetchrow('SELECT * FROM "Agent".licenses WHERE license_key = $1', license_key)
    await conn.close()
    if license_data:
        return License(**license_data)
    return None

async def has_access(user_id: str, agent_id: str) -> bool:
    conn = await get_conn()
    license_data = await conn.fetchrow(
        'SELECT * FROM "Agent".licenses WHERE user_id = $1 AND agent_id = $2 AND is_active = TRUE',
        user_id, agent_id
    )
    await conn.close()
    return license_data is not None
