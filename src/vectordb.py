import os
import json
from typing import List, Optional, Dict, Any
import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as Connection
from src.config import settings


def get_conn() -> Optional[Connection]:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return None
    return psycopg2.connect(db_url)


def upsert_cases(cases: List[Dict[str, Any]]):
    conn = get_conn()
    if conn is None:
        raise RuntimeError("DATABASE_URL not configured")

    with conn:
        with conn.cursor() as cur:
            for c in cases:
                cur.execute(
                    "INSERT INTO case_vectors (case_id, title, description, solution, embedding) VALUES (%s,%s,%s,%s,%s)",
                    (c.get("id"), c.get("title"), c.get("description"), c.get("solution"), json.dumps(c.get("embedding"))),
                )


def query_similar(description: str, top_k: int = 3) -> List[Dict[str, Any]]:
    # This is a naive similarity query: we assume embeddings are stored and do a linear scan computing cosine similarity.
    # For production, use pgvector extension or a specialized vector DB.
    conn = get_conn()
    if conn is None:
        return []

    # compute embedding for query using OpenAI if available
    from src.agents.llm import call_openai_for_summary
    try:
        emb = None
        if settings.OPENAI_API_KEY:
            # Use OpenAI embedding endpoint if available; keep simple by using summary adapter's model to simulate
            # WARNING: this is a placeholder; in production call openai.Embedding.create
            emb = [0.0]
    except Exception:
        emb = None

    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, case_id, title, description, solution, embedding FROM case_vectors")
            rows = cur.fetchall()

    results = []
    for r in rows:
        # naive matching: check if any fact or description token overlap
        score = 0.0
        if description and r.get("description"):
            if description in r.get("description") or r.get("description") in description:
                score = 1.0
        if score > 0:
            results.append({"score": score, "row": r})

    results.sort(key=lambda x: x["score"], reverse=True)
    return [r["row"] for r in results[:top_k]]
