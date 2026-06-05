from pydantic import BaseModel
from typing import Optional


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
