from src.models.greeting import Greeting


def make_greeting(name: str) -> Greeting:
    """Create a Greeting model for the given name."""
    return Greeting(message=f"Hello, {name}!")
