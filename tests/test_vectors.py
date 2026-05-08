from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app
from src.config import settings


def get_auth_header(client: TestClient):
    resp = client.post("/token", data={"username": settings.DEMO_USERNAME, "password": settings.DEMO_PASSWORD})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_vectors_insert_happy_path():
    client = TestClient(app)
    headers = get_auth_header(client)

    payload = {
        "cases": [
            {"id": "c1", "title": "T1", "description": "desc1", "solution": "sol1", "embedding": [0.1, 0.2]},
            {"id": "c2", "title": "T2", "description": "desc2", "solution": "sol2"},
        ]
    }

    with patch("src.vectordb.upsert_cases") as mock_upsert:
        mock_upsert.return_value = None
        r = client.post("/agents/vectors", json=payload, headers=headers)
        assert r.status_code == 200
        assert r.json().get("inserted") == 2
        mock_upsert.assert_called_once()


def test_vectors_insert_bad_payload():
    client = TestClient(app)
    headers = get_auth_header(client)

    payload = {"not_cases": []}
    r = client.post("/agents/vectors", json=payload, headers=headers)
    assert r.status_code == 400
