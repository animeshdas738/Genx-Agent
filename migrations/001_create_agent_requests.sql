-- Migration: Create Agent.agent_requests table to log agent requests and responses
CREATE SCHEMA IF NOT EXISTS "Agent";

CREATE TABLE IF NOT EXISTS "Agent".agent_requests (
    id BIGSERIAL PRIMARY KEY,
    request_id TEXT,
    case_id TEXT,
    endpoint TEXT NOT NULL,
    payload JSONB,
    response JSONB,
    model TEXT,
    confidence DOUBLE PRECISION,
    tokens INTEGER,
    status TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_requests_created_at ON "Agent".agent_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_requests_case_id ON "Agent".agent_requests(case_id);

SELECT * FROM "Agent".agent_requests;