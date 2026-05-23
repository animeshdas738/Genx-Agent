-- Migration: add api_keys table to the Agent schema
-- Each user can have multiple named API keys; only the SHA-256 hash is stored.

CREATE TABLE IF NOT EXISTS "Agent".api_keys (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES "Agent".users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) NOT NULL UNIQUE,   -- SHA-256 hex digest of the raw key
    key_prefix VARCHAR(12) NOT NULL,        -- first 12 chars of the raw key, shown in listings
    name VARCHAR(100),                      -- optional user-defined label
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ                  -- NULL = never expires
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id  ON "Agent".api_keys (user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON "Agent".api_keys (key_hash);
