from fastapi import APIRouter, Depends, Request
from src.security import get_current_user
from src.agents.tools import SummarizeTool
from src.agents.models import CaseDetail, CaseSummary
import json

router = APIRouter(prefix="/agents", tags=["agents"])


tool = SummarizeTool()


@router.post("/summarize", response_model=CaseSummary)
async def summarize(request: Request, user: str = Depends(get_current_user)):
    """Summarize the provided case details and suggest a solution with confidence score.

    Accepts either JSON body or form-encoded body for easier curl usage.
    """
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
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Missing required field: description")

    return tool.run(data)
