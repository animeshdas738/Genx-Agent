"""Small demo application."""

def greet(name: str) -> str:
    """Return a greeting for the given name.

    Args:
        name: the name to greet

    Returns:
        A greeting string.
    """
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet("World"))
