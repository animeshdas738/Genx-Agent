from pydantic import BaseModel, Field
from typing import List, Optional


class CaseDetail(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: str
    facts: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[dict] = None
    context: Optional[str] = None


class CaseSummary(BaseModel):
    summary: str
    suggested_solution: str
    confidence: float = Field(ge=0.0, le=1.0)
    tokens: Optional[int] = None
    # similarity is the raw similarity score returned by the vector DB (cosine similarity)
    similarity: Optional[float] = None
    # arbitrary extra metadata returned by the LLM (revenue, employees, etc.)
    extra: Optional[dict] = None


# Generic tool IO models so tools can reuse the same shapes.
class BaseToolInput(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    facts: Optional[list] = Field(default_factory=list)
    metadata: Optional[dict] = None
    context: Optional[str] = None


class BaseToolOutput(BaseModel):
    summary: Optional[str] = None
    suggested_solution: Optional[str] = None
    confidence: Optional[float] = None
    tokens: Optional[int] = None
    extra: Optional[dict] = None


class CaseResolutionInput(BaseModel):
    subject: str
    description: str


class CaseResolutionOutput(BaseModel):
    resolution: str
    confidence: Optional[float] = None
    source: str  # "vector_db" | "llm" | "unresolved"
    similarity: Optional[float] = None
    tokens: Optional[int] = None


class SentimentAnalysisInput(BaseModel):
    text: str
    context: Optional[str] = None
    metadata: Optional[dict] = None


class SentimentAnalysisOutput(BaseModel):
    sentiment: str  # "positive" | "negative" | "neutral"
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    tokens: Optional[int] = None
