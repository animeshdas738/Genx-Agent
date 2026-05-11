import os
import json
import math
from typing import List, Optional, Dict, Any
from uuid import uuid4

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as Connection
from src.config import settings
from psycopg2 import sql

try:
    # LangChain embedding wrapper
    from langchain.embeddings import OpenAIEmbeddings
except Exception:
    OpenAIEmbeddings = None


def get_conn() -> Optional[Connection]:
    db_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    if not db_url:
        return None
    return psycopg2.connect(db_url)


def _compute_embedding(text: str) -> List[float]:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set in settings; cannot compute embeddings")

    # Prefer LangChain if available
    if OpenAIEmbeddings is not None:
        emb = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        vectors = emb.embed_documents([text])
        vec = vectors[0]
        try:
            return [float(x) for x in vec]
        except Exception as e:
            raise RuntimeError(f"Failed to coerce LangChain embedding to list of floats: {e}")

    # Fallback: use openai directly. Support both openai>=1.0.0 (OpenAI client) and older versions.
    try:
        import openai

        embedding_model = getattr(settings, "OPENAI_EMBEDDING_MODEL", None) or "text-embedding-3-small"

        # Newer openai Python library (>=1.0.0) exposes an OpenAI client
        client_cls = getattr(openai, "OpenAI", None)
        if client_cls is not None:
            client = client_cls(api_key=settings.OPENAI_API_KEY)
            resp = client.embeddings.create(model=embedding_model, input=text)
            # resp may be a dict-like or object with .data
            try:
                vec = resp.data[0].embedding
            except Exception:
                vec = resp["data"][0]["embedding"]
            return [float(x) for x in vec]

        # Fallback to legacy API
        openai.api_key = settings.OPENAI_API_KEY
        resp = openai.Embedding.create(model=embedding_model, input=text)
        vec = resp["data"][0]["embedding"]
        return [float(x) for x in vec]
    except Exception as e:
        raise RuntimeError(f"Failed to compute embedding with OpenAI SDK: {e}")


def upsert_cases(cases: List[Dict[str, Any]]):
    conn = get_conn()
    if conn is None:
        raise RuntimeError("DATABASE_URL not configured")
    cur = None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        for c in cases:
            case_id = c.get("id") or str(uuid4())
            title = c.get("title")
            description = c.get("description")
            solution = c.get("solution")
            embedding = c.get("embedding")

            # If embedding not provided, compute via LangChain/OpenAI
            if not embedding:
                text = (title or "") + "\n" + (description or "")
                # Compute embedding; let exceptions propagate so caller sees failures
                print(f"[vectordb] computing embedding for case_id={case_id}")
                embedding = _compute_embedding(text)
                print(f"[vectordb] embedding computed (len={len(embedding) if embedding else 0}) for case_id={case_id}")

            # Upsert: update if case_id exists, otherwise insert
            # Build schema-qualified identifier if CASE_VECTOR_SCHEMA set
            schema = settings.CASE_VECTOR_SCHEMA
            if schema:
                tbl = sql.Identifier(schema, "case_vectors")
            else:
                tbl = sql.Identifier("case_vectors")
            print('tbl' + str(tbl))

            cur.execute(sql.SQL("SELECT id FROM {} WHERE case_id = %s").format(tbl), (case_id,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    sql.SQL("UPDATE {} SET title=%s, description=%s, solution=%s, embedding=%s WHERE case_id=%s").format(tbl),
                    (title, description, solution, json.dumps(embedding) if embedding is not None else None, case_id),
                )
            else:
                cur.execute(
                    sql.SQL("INSERT INTO {} (case_id, title, description, solution, embedding) VALUES (%s,%s,%s,%s,%s)").format(tbl),
                    (case_id, title, description, solution, json.dumps(embedding) if embedding is not None else None),
                )

        # Explicitly commit so changes are visible to other connections
        conn.commit()
    finally:
        if cur is not None:
            cur.close()
        try:
            conn.close()
        except Exception:
            pass


def similarity_to_confidence(similarity: float, min_conf: float = 0.5, max_conf: float = 0.99) -> Optional[float]:
    """Map a raw cosine similarity score to a bounded confidence value.

    - similarity: raw cosine similarity (expected in [0,1]).
    - values below settings.CASE_SIMILARITY_THRESHOLD return None.
    - maps [threshold, 1.0] -> [min_conf, max_conf] linearly and clamps.
    """
    if similarity is None:
        return None
    try:
        s = float(similarity)
    except Exception:
        return None

    thr = float(getattr(settings, "CASE_SIMILARITY_THRESHOLD", 0.5))
    if s <= thr:
        return None
    # normalize to [0,1]
    norm = (s - thr) / (1.0 - thr) if (1.0 - thr) > 0 else 1.0
    conf = min_conf + norm * (max_conf - min_conf)
    # clamp
    conf = max(min_conf, min(conf, max_conf))
    return round(conf, 3)


def query_similar(description: str, top_k: int = 3) -> List[Dict[str, Any]]:
    conn = get_conn()
    if conn is None:
        return []
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            schema = settings.CASE_VECTOR_SCHEMA
            if schema:
                tbl = sql.Identifier(schema, "case_vectors")
            else:
                tbl = sql.Identifier("case_vectors")

            cur.execute(sql.SQL("SELECT case_id, title, description, solution, embedding FROM {}").format(tbl))
            rows = cur.fetchall()
    # compute embedding for query
    try:
        q_emb = _compute_embedding(description)
    except Exception:
        q_emb = None
    
    results: List[Dict[str, Any]] = []
    for r in rows:
        emb = r.get("embedding")
        # if stored as JSON string, try to load
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except Exception:
                emb = None

        if not emb or not q_emb:
            # fallback: substring match (very coarse)
            score = 1.0 if (description and r.get("description") and (description in r.get("description") or r.get("description") in description)) else 0.0
        else:
            try:
                a = list(emb)
                b = list(q_emb)
                dot = sum(x * y for x, y in zip(a, b))
                norma = math.sqrt(sum(x * x for x in a))
                normb = math.sqrt(sum(y * y for y in b))
                score = (dot / (norma * normb)) if norma and normb else 0.0
            except Exception:
                score = 0.0
    # Only include sufficiently similar rows
        if score > settings.CASE_SIMILARITY_THRESHOLD:
            try:
                r["similarity"] = float(score)
            except Exception:
                r["similarity"] = None
            r["tokens"] = None
            results.append({"score": score, "row": r})

    # Sort by score desc and return the top_k rows (augmented)
    results.sort(key=lambda x: x["score"], reverse=True)
    #print('Line 202------results: ' + str(results))
    return [r["row"] for r in results[:top_k]]
