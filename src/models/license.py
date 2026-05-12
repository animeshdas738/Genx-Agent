from pydantic import BaseModel
from typing import Optional
import datetime

class License(BaseModel):
    id: Optional[int] = None
    user_id: str
    agent_id: str
    license_key: str
    is_active: bool = True
    created_at: Optional[datetime.datetime] = None
    expires_at: Optional[datetime.datetime] = None
