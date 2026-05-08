-- Migration: Create table to store case embeddings and solutions
CREATE TABLE IF NOT EXISTS case_vectors (
    id BIGSERIAL PRIMARY KEY,
    case_id TEXT,
    title TEXT,
    description TEXT NOT NULL,
    solution TEXT,
    embedding JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_case_vectors_case_id ON case_vectors(case_id);
CREATE INDEX IF NOT EXISTS idx_case_vectors_created_at ON case_vectors(created_at);
