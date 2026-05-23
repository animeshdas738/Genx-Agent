import hashlib
import secrets
from typing import Optional

import asyncpg

from src.config import settings

_PREFIX = "genx_"
_RAW_KEY_BYTES = 32  # 64 hex chars


def _generate_raw_key() -> str:
    return _PREFIX + secrets.token_hex(_RAW_KEY_BYTES)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def _get_conn():
    return await asyncpg.connect(settings.DATABASE_URL)


async def create_api_key(user_id: int, name: Optional[str] = None) -> dict:
    raw_key = _generate_raw_key()
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:12]

    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO "Agent".api_keys (user_id, key_hash, key_prefix, name)
            VALUES ($1, $2, $3, $4)
            RETURNING id, key_prefix, name, is_active, created_at, expires_at
            """,
            user_id, key_hash, key_prefix, name,
        )
    finally:
        await conn.close()

    return {**dict(row), "key": raw_key}  # raw key returned only here


async def get_api_keys_for_user(user_id: int) -> list[dict]:
    conn = await _get_conn()
    try:
        rows = await conn.fetch(
            """
            SELECT id, key_prefix, name, is_active, created_at, last_used_at, expires_at
            FROM "Agent".api_keys
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id,
        )
    finally:
        await conn.close()
    return [dict(r) for r in rows]


async def get_user_by_api_key(raw_key: str) -> Optional[dict]:
    key_hash = _hash_key(raw_key)
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.username, u.is_active, ak.id AS key_id, ak.expires_at
            FROM "Agent".api_keys ak
            JOIN "Agent".users u ON u.id = ak.user_id
            WHERE ak.key_hash = $1
              AND ak.is_active = TRUE
              AND u.is_active = TRUE
              AND (ak.expires_at IS NULL OR ak.expires_at > now())
            """,
            key_hash,
        )
        if row:
            # Update last_used_at without blocking the response
            await conn.execute(
                'UPDATE "Agent".api_keys SET last_used_at = now() WHERE id = $1',
                row["key_id"],
            )
    finally:
        await conn.close()
    return dict(row) if row else None


async def revoke_api_key(key_id: int, user_id: int) -> bool:
    conn = await _get_conn()
    try:
        result = await conn.execute(
            """
            UPDATE "Agent".api_keys
            SET is_active = FALSE
            WHERE id = $1 AND user_id = $2
            """,
            key_id, user_id,
        )
    finally:
        await conn.close()
    return result == "UPDATE 1"
