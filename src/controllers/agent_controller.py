from typing import List
from fastapi import APIRouter, Depends, HTTPException
from src.security import get_current_user
from src.models.agent import AgentInfo
from src.services import agent_service

router = APIRouter(tags=["agents"])


@router.get("", response_model=List[AgentInfo])
async def list_agents(user: str = Depends(get_current_user)):
    """Return all agents the current user is licensed to access."""
    try:
        return await agent_service.get_licensed_agents(user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
