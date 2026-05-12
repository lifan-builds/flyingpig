"""Tests for the FastAPI endpoints."""

from fastapi.testclient import TestClient
from src.api.auth import get_current_user
from src.api.main import app
from src.models.user import User


async def override_get_current_user():
    return User(id=1, username="testuser")


app.dependency_overrides[get_current_user] = override_get_current_user


class TestAPI:
    def test_health(self):
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_list_sites(self):
        with TestClient(app) as client:
            response = client.get("/sites")
            assert response.status_code == 200
            assert "amex" in response.json()["sites"]
            assert "oura" in response.json()["sites"]
            assert "generic" in response.json()["sites"]

    def test_get_amex_templates(self):
        with TestClient(app) as client:
            response = client.get("/sites/amex/templates")
            assert response.status_code == 200
            data = response.json()
            assert data["site"] == "amex"
            template_ids = [t["id"] for t in data["templates"]]
            assert "negotiate_fee" in template_ids
            assert "dispute_charge" in template_ids

    def test_get_all_templates(self):
        with TestClient(app) as client:
            response = client.get("/templates")
            assert response.status_code == 200
            data = response.json()
            assert "amex" in data
            assert len(data["amex"]) >= 4

    def test_create_task_invalid_site(self):
        with TestClient(app) as client:
            response = client.post(
                "/tasks",
                json={"site": "nonexistent", "task": "test"},
            )
            assert response.status_code == 400

    def test_launch_browser_returns_cdp_url(self, monkeypatch):
        captured = {}

        def fake_launch(config):
            captured["config"] = config
            return "http://127.0.0.1:9222"

        monkeypatch.setattr("src.api.main.launch_cdp_chrome", fake_launch)

        with TestClient(app) as client:
            response = client.post("/browser/launch", json={"site": "amex"})

        assert response.status_code == 200
        assert response.json()["cdp_url"] == "http://127.0.0.1:9222"
        assert captured["config"].chrome_profile == "default"
        assert captured["config"].initial_url.startswith("https://")
        assert captured["config"].dashboard_url is None

    def test_get_task_not_found(self):
        with TestClient(app) as client:
            response = client.get("/tasks/nonexistent")
            assert response.status_code == 404
