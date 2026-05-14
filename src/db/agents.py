import asyncio
from typing import Optional

import asyncpg

from src.config import settings


_pool: Optional[asyncpg.pool.Pool] = None


async def get_pool() -> asyncpg.pool.Pool:
    global _pool
    if _pool is None:
        if not settings.DATABASE_URL:
            raise RuntimeError("DATABASE_URL not configured")
        _pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
    return _pool


async def fetch_prompt_for_tool(tool_id: str) -> Optional[str]:
    """Return the prompt_text for a given tool_id or None if not found."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT prompt_text FROM "Agent".prompts WHERE tool_id = $1 ORDER BY id DESC LIMIT 1', tool_id)
        if row:
            return row['prompt_text']
    return None


async def fetch_tool_metadata(tool_id: str) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT tool_id, name, description, metadata FROM "Agent".tools WHERE tool_id = $1', tool_id)
        if row:
            return dict(row)
    return None


async def fetch_agent(agent_id: str) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT agent_id, name, description, is_active FROM "Agent".agents WHERE agent_id = $1', agent_id)
        if row:
            return dict(row)
    return None
