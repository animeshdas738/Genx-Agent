from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from src.services import license_service
from src.security import get_current_user
from src.models.license import License
from pydantic import BaseModel, ValidationError
import json

router = APIRouter(prefix="/licenses", tags=["licenses"])


class LicenseRequest(BaseModel):
    user_id: str
    agent_id: str


@router.post("/", response_model=License)
async def create_license_endpoint(request: Request, user: str = Depends(get_current_user)):
    """
    Creates a new license for a user and agent. This endpoint now logs raw request
    data to help diagnose 422/validation issues.
    """
    print(f"[DEBUG] create_license_endpoint called by user: {user}")

    # Read raw body for debugging. FastAPI will not have validated anything yet when
    # we do this because we're accepting the Request object directly.
    raw = await request.body()
    raw_text = raw.decode(errors="ignore") if raw else ""

    parsed = None
    # Try to parse JSON first, else try form data
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            parsed = json.loads(raw_text) if raw_text else {}
        else:
            form = await request.form()
            parsed = {k: form.get(k) for k in form.keys()} if form else {}
    except Exception as e:
        print(f"[DEBUG] Failed to parse incoming body: {e}")
        parsed = None

    # Validate into Pydantic model so we can return clearer errors and log details
    if not parsed or not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="Request body must be JSON or form data with user_id and agent_id")

    try:
        lr = LicenseRequest(**parsed)
    except ValidationError as ve:
        # Re-raise as 422 with the pydantic errors
        raise HTTPException(status_code=422, detail=ve.errors())

    try:
        new_license = await license_service.create_license(lr.user_id, lr.agent_id)
        print(f"[DEBUG] License created successfully: {new_license}")
        return new_license
    except Exception as e:
        import traceback
        print(f"[DEBUG] An error occurred: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
