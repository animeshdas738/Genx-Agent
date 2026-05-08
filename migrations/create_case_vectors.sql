-- Migration: Create table to store case embeddings and solutions
CREATE TABLE IF NOT EXISTS "Agent".case_vectors (
    id BIGSERIAL PRIMARY KEY,
    case_id TEXT,
    title TEXT,
    description TEXT NOT NULL,
    solution TEXT,
    embedding JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_case_vectors_case_id ON "Agent".case_vectors(case_id);
CREATE INDEX IF NOT EXISTS idx_case_vectors_created_at ON "Agent".case_vectors(created_at);


SELECT * FROM "Agent".case_vectors;

DELETE FROM "Agent".case_vectors WHERE case_id = '00073d8e-02fe-435a-9a55-e052038fa2f3';