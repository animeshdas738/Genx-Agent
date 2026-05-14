from fastapi import APIRouter, Depends, Request, HTTPException
from src.security import get_current_user
from src.agents.tools import SummarizeTool
from src.agents.models import CaseDetail, CaseSummary
from src.vectordb import query_similar, upsert_cases, similarity_to_confidence
from src.db.agent_requests import insert_agent_request
from src.services import license_service
import json

router = APIRouter(prefix="/agents", tags=["agents"])


tool = SummarizeTool()

@router.post("/summarize", response_model=CaseSummary)
async def summarize(request: Request, user: str = Depends(get_current_user)):
    """Summarize the provided case details and suggest a solution with confidence score.

    Accepts either JSON body or form-encoded body for easier curl usage.
    """
    agent_id = "summarize_agent"
    if not await license_service.has_access(user, agent_id):
        raise HTTPException(status_code=403, detail="Resource is not available.")
    
    content_type = request.headers.get("content-type", "")
    data = None

    if "application/json" in content_type:
        data = await request.json()
        # if client sent an empty body, request.json() can return None
        if data is None:
            data = {}
    else:
        # attempt to parse form data
        form = await request.form()
        data = {}
        for key in form.keys():
            data[key] = form.get(key)
        # coerce facts and metadata if supplied as JSON strings
        if "facts" in data and isinstance(data["facts"], str):
            try:
                data["facts"] = json.loads(data["facts"])
            except Exception:
                # fallback: split on commas
                data["facts"] = [f.strip() for f in data["facts"].split(",") if f.strip()]
        if "metadata" in data and isinstance(data["metadata"], str):
            try:
                data["metadata"] = json.loads(data["metadata"])
            except Exception:
                data["metadata"] = {"raw": data["metadata"]}

    # Validate/coerce into CaseDetail via the tool which will construct CaseDetail
    # If body is empty and client sent plain text, use it as description
    if not data:
        # try reading raw text
        text = (await request.body()).decode(errors="ignore").strip()
        if text:
            data = {"description": text}

    # Ensure description exists before building CaseDetail to avoid 500
    if not data or "description" not in data or not str(data.get("description") or "").strip():
        raise HTTPException(status_code=400, detail="Missing required field: description")

    # Before calling the LLM summarizer, check the vector DB for a probable stored solution.
    try:
        matches = query_similar(str(data.get("description") or ""), top_k=1)
    except Exception:
        matches = []
    if matches:
        context = "Found similar cases:\n"
        for m in matches:
            context += f"- {m.get('title')}: {m.get('description')}\n"
        data["context"] = context

    #print(f"[agents.controller] vector DB query returned {len(matches)} matches for description: {data.get('description')[:100]}...")
    if matches:
        # Use the top match and return it as a CaseSummary. The DB stores a solution and description.
        m = matches[0]
        # If the DB row contains a stored confidence, trust it. Otherwise call the LLM summarizer
        # to compute a confidence and tokens for the matched solution.
        #print('m-------' + str(m))
        stored_conf = m.get("similarity")
        #print('stored_conf====' + str(stored_conf))
        stored_summary = m.get("description") or ""
        stored_solution = m.get("solution") or "Solution retrieved from vector DB"
        # stored_conf is the raw similarity (from vectordb). Map it to a calibrated
        # confidence value for display and decision-making.
        try:
            stored_similarity = float(stored_conf) if stored_conf is not None else None
        except Exception:
            stored_similarity = None

        mapped_conf = similarity_to_confidence(stored_similarity) if stored_similarity is not None else None
        print(f"[agents.controller] top vector DB match has similarity={stored_similarity}, mapped_confidence={mapped_conf}, summary='{stored_summary[:100]}...', solution='{stored_solution[:100]}...'")
        # Only treat this as a retrieved (trusted) match when mapping produced a confidence
        if mapped_conf is not None:
            # Use stored values; coerce summary length for display
            summary_text = stored_summary
            if summary_text and len(summary_text) > 200:
                summary_text = summary_text[:197] + "..."
            result = CaseSummary(
                summary=summary_text or (data.get("description")[:200] if data.get("description") else ""),
                suggested_solution=stored_solution,
                confidence=float(mapped_conf),
                tokens=m.get("tokens") if m.get("tokens") is not None else None,
                similarity=float(stored_similarity) if stored_similarity is not None else None,
            )
            print(f"[agents.controller] returning retrieved match with confidence {result.confidence} for case_id={m.get('case_id') or m.get('caseId')}")
            # log the retrieval event
            try:
                print(f"[agents.controller] attempting to insert_agent_request for retrieved match case_id={m.get('case_id') or m.get('caseId')}")
                insert_agent_request(
                    endpoint="/agents/summarize",
                    payload={"description": data.get("description"), "title": data.get("title")},
                    response=result.model_dump(),
                    case_id=m.get("case_id") or m.get("caseId") or None,
                    model=None,
                    confidence=float(mapped_conf) if mapped_conf is not None else None,
                    tokens=m.get("tokens") if m.get("tokens") is not None else None,
                    status="retrieved",
                )
                print(f"[agents.controller] insert_agent_request returned successfully for retrieved match")
            except Exception as e:
                import traceback

                print(f"[agents.controller] failed to log retrieved agent request: {e}")
                print(traceback.format_exc())

            return result.model_dump()

        # No stored confidence -> call the summarizer to get LLM-derived confidence/tokens
        try:
            # Build a minimal input for the summarizer using the stored description/title
            summarize_input = {"title": m.get("title"), "description": m.get("description"), "facts": []}
            llm_result = tool.run(summarize_input)
            # tool.run returns a dict with summary, suggested_solution, confidence, tokens
            return llm_result
        except Exception:
            # As a last resort, fall back to a conservative confidence but do not hardcode 0.95
            summary_text = (m.get("description") or "")
            if summary_text and len(summary_text) > 200:
                summary_text = summary_text[:197] + "..."
            result = CaseSummary(
                summary=summary_text or (data.get("description")[:200] if data.get("description") else ""),
                suggested_solution=stored_solution,
                confidence=0.5,
                tokens=None,
            )
            return result.model_dump()

    # No vector DB match -> use LLM summarizer tool
    result = tool.run(data)

    # Try to log the agent request/response
    try:
        insert_agent_request(
            endpoint="/agents/summarize",
            payload=data,
            response=result,
            case_id=data.get("id") or None,
            model=None,
            confidence=result.get("confidence") if isinstance(result, dict) else None,
            tokens=result.get("tokens") if isinstance(result, dict) else None,
            status="generated",
        )
    except Exception as e:
        import traceback

        print(f"[agents.controller] failed to log generated agent request: {e}")
        print(traceback.format_exc())

    return result



@router.post("/vectors")
async def insert_vectors(request: Request, user: str = Depends(get_current_user)):
    """Insert a list of case vectors into the DB. Payload should be {"cases": [ ... ]}.

    Accepts JSON body, form-encoded body (with 'cases' as JSON string) or raw JSON text.
    Each case may include: id, title, description, solution, embedding (list of floats).
    """
    content_type = request.headers.get("content-type", "")
    data = None

    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            # fall through to try raw body
            data = None
    else:
        # try form
        form = await request.form()
        if form:
            # If 'cases' was sent as a JSON string in a form
            if "cases" in form:
                raw = form.get("cases")
                try:
                    data = {"cases": json.loads(raw)} if isinstance(raw, str) else {"cases": raw}
                except Exception:
                    # maybe it's already a list-like
                    data = {"cases": raw}
            else:
                # coerce other fields if necessary
                data = {k: form.get(k) for k in form.keys()}

    if data is None:
        # try reading raw body and parsing as json
        try:
            raw = (await request.body()).decode(errors="ignore").strip()
            if raw:
                data = json.loads(raw)
        except Exception:
            data = None

    cases = data.get("cases") if isinstance(data, dict) else None
    if not cases or not isinstance(cases, list):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Payload must include a 'cases' list")

    # Normalize entries and validate required fields
    normalized = []
    for idx, c in enumerate(cases):
        if not isinstance(c, dict):
            raise HTTPException(status_code=400, detail=f"Each case must be an object/dict (index {idx})")
        title = c.get("title")
        description = c.get("description")
        solution = c.get("solution")
        if not title or not description:
            raise HTTPException(status_code=400, detail=f"Each case must include 'title' and 'description' (index {idx})")

        normalized.append({
            "id": c.get("id"),
            "title": title,
            "description": description,
            "solution": solution,
            "embedding": c.get("embedding"),
        })

    try:
        upsert_cases(normalized)
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))

    return {"inserted": len(normalized)}
