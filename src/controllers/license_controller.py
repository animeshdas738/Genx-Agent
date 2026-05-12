from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from src.services import license_service
from src.security import get_current_user
from src.models.license import License
from pydantic import BaseModel

router = APIRouter(prefix="/licenses", tags=["licenses"])

class LicenseRequest(BaseModel):
    user_id: str
    agent_id: str

@router.post("/", response_model=License)
async def create_license_endpoint(request: LicenseRequest, user: str = Depends(get_current_user)):
    """
    Creates a new license for a user and agent.
    """
    print(f"[DEBUG] create_license_endpoint called by user: {user}")
    print(f"[DEBUG] Request body: user_id={request.user_id}, agent_id={request.agent_id}")
    # For now, any authenticated user can create a license.
    # In a real application, you'd want to restrict this to admins.
    try:
        new_license = await license_service.create_license(request.user_id, request.agent_id)
        print(f"[DEBUG] License created successfully: {new_license}")
        return new_license
    except Exception as e:
        import traceback
        print(f"[DEBUG] An error occurred: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
