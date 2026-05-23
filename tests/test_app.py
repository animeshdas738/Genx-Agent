from src.services.greeting_service import make_greeting
from src.main import app
from fastapi.testclient import TestClient
from src.config import settings


def test_service_greeting():
    g = make_greeting("Alice")
    assert g.message == "Hello, Alice!!"


def test_api_hello_with_jwt():
    client = TestClient(app)

    # Obtain token using demo credentials from settings
    token_resp = client.post("/token", data={"username": settings.DEMO_USERNAME, "password": settings.DEMO_PASSWORD})
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/hello", params={"name": "Bob"}, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"message": "Hello, Bob!"}


def test_agent_summarize_endpoint():
    client = TestClient(app)
    token_resp = client.post("/token", data={"username": settings.DEMO_USERNAME, "password": settings.DEMO_PASSWORD})
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "id": "case-1",
        "title": "Example case",
        "description": "This case describes a user who encountered an error while uploading a file. The file size was 5MB and the system returned HTTP 413.",
        "facts": ["file size 5MB", "HTTP 413 returned"],
    }

    r = client.post("/agents/summarize", json=payload, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body and "suggested_solution" in body and "confidence" in body
    assert 0.0 <= body["confidence"] <= 1.0
