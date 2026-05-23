from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: Optional[str] = None


class ApiKeyCreated(BaseModel):
    id: int
    key: str           # raw key — shown only once
    key_prefix: str
    name: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]


class ApiKeyInfo(BaseModel):
    id: int
    key_prefix: str
    name: Optional[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
