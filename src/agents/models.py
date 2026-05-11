from pydantic import BaseModel, Field
from typing import List, Optional


class CaseDetail(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: str
    facts: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[dict] = None


class CaseSummary(BaseModel):
    summary: str
    suggested_solution: str
    confidence: float = Field(ge=0.0, le=1.0)
    tokens: Optional[int] = None
    # similarity is the raw similarity score returned by the vector DB (cosine similarity)
    similarity: Optional[float] = None
