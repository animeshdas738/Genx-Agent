from fastapi import APIRouter, Depends
from src.services.greeting_service import make_greeting
from src.security import get_current_user

router = APIRouter()


@router.get("/hello", name="hello")
def hello(name: str = "World", user: str = Depends(get_current_user)):
    """Return a greeting JSON using the service layer. Requires JWT Bearer token."""
    greeting = make_greeting(name)
    # Pydantic v2: use model_dump()
    return greeting.model_dump()
