from src.services.greeting_service import make_greeting
from src.main import app
from fastapi.testclient import TestClient


def test_service_greeting():
    g = make_greeting("Alice")
    assert g.message == "Hello, Alice!"


def test_api_hello():
    client = TestClient(app)
    r = client.get("/hello", params={"name": "Bob"})
    assert r.status_code == 200
    assert r.json() == {"message": "Hello, Bob!"}
