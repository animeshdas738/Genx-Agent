from fastapi import APIRouter
from src.services.greeting_service import make_greeting

router = APIRouter()


@router.get("/hello", name="hello")
def hello(name: str = "World"):
    """Return a greeting JSON using the service layer."""
    greeting = make_greeting(name)
    return greeting.dict()
