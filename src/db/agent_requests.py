import os
import json
from typing import Optional, Dict, Any
from uuid import uuid4

import psycopg2
import psycopg2.extras
from psycopg2 import sql
from src.config import settings


def get_conn():
    db_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    if not db_url:
        return None
    return psycopg2.connect(db_url)


def insert_agent_request(
    endpoint: str,
    payload: Dict[str, Any],
    response: Dict[str, Any],
    case_id: Optional[str] = None,
    model: Optional[str] = None,
    confidence: Optional[float] = None,
    tokens: Optional[int] = None,
    status: str = "ok",
    metadata: Optional[Dict[str, Any]] = None,
):
    """Insert a log row into Agent.agent_requests. Returns the generated request_id."""
    conn = get_conn()
    if conn is None:
        raise RuntimeError("DATABASE_URL not configured")

    req_id = str(uuid4())


    # Try several schema candidates to be resilient against how migrations were
    # applied (quoted vs unquoted schema names). We try in this order:
    # 1) the exact configured schema name (preserve case),
    # 2) the lowercase variant of the configured name,
    # 3) the uppercase variant,
    # 4) unqualified table name (no schema).
    schema_setting = settings.CASE_VECTOR_SCHEMA or "Agent"
    candidates = [schema_setting, schema_setting.lower(), schema_setting.upper(), None]

    last_exc = None
    inserted = False
    for candidate in candidates:
        cur = None
        try:
            tbl = sql.Identifier(candidate, "agent_requests") if candidate is not None else sql.Identifier("agent_requests")
            print(f"[agent_requests] attempting to insert request {req_id} into schema={candidate or '<default>'} for case_id={case_id}")
            cur = conn.cursor()
            cur.execute(
                sql.SQL("INSERT INTO {} (request_id, case_id, endpoint, payload, response, model, confidence, tokens, status, metadata) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)").format(tbl),
                (
                    req_id,
                    case_id,
                    endpoint,
                    json.dumps(payload) if payload is not None else None,
                    json.dumps(response) if response is not None else None,
                    model,
                    confidence,
                    tokens,
                    status,
                    json.dumps(metadata) if metadata is not None else None,
                ),
            )
            conn.commit()
            print(f"[agent_requests] inserted request {req_id} into schema={candidate or '<default>'}")
            inserted = True
            break
        except Exception as e:
            # Record and log; try next candidate. Rollback to clear transaction state.
            last_exc = e
            try:
                conn.rollback()
            except Exception:
                pass
            print(f"[agent_requests] insert attempt into schema={candidate or '<default>'} failed: {e}")
        finally:
            if cur is not None:
                try:
                    cur.close()
                except Exception:
                    pass

    try:
        conn.close()
    except Exception:
        pass

    if not inserted:
        # Surface the last error to the caller for debugging
        print(f"[agent_requests] all insert attempts failed for request {req_id}: {last_exc}")
        raise last_exc

    return req_id
