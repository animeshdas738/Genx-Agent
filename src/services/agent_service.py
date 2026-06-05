from typing import List
import asyncpg
from src.config import settings
from src.models.agent import AgentInfo


async def get_conn():
    return await asyncpg.connect(settings.DATABASE_URL)


async def get_licensed_agents(user_id: str) -> List[AgentInfo]:
    conn = await get_conn()
    try:
        rows = await conn.fetch(
            """
            SELECT a.agent_id, a.name, a.label, a.description, a.is_active
            FROM "Agent".agents a
            INNER JOIN "Agent".licenses l ON l.agent_id = a.agent_id
            WHERE l.user_id = $1
              AND l.is_active = TRUE
              AND a.is_active = TRUE
              AND (l.expires_at IS NULL OR l.expires_at > now())
            ORDER BY a.name
            """,
            user_id,
        )
        return [AgentInfo(**dict(row)) for row in rows]
    finally:
        await conn.close()
