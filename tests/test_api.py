from __future__ import annotations

import importlib

from fastapi.testclient import TestClient


def test_health_and_notes(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWCASE_DB_PATH", str(tmp_path / "showcase.db"))

    memory_store = importlib.import_module("src.memory.store")
    importlib.reload(memory_store)
    scheduler_module = importlib.import_module("src.scheduler.service")
    importlib.reload(scheduler_module)
    app_module = importlib.import_module("src.api.app")
    importlib.reload(app_module)

    client = TestClient(app_module.app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    note = client.post("/notes", json={"title": "Recruiter note", "content": "Show backend architecture", "category": "portfolio"})
    assert note.status_code == 200

    notes = client.get("/notes")
    assert notes.status_code == 200
    assert len(notes.json()["notes"]) == 1


def test_voice_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWCASE_DB_PATH", str(tmp_path / "showcase.db"))

    memory_store = importlib.import_module("src.memory.store")
    importlib.reload(memory_store)
    app_module = importlib.import_module("src.api.app")
    importlib.reload(app_module)

    client = TestClient(app_module.app)

    result = client.post("/voice/mock/transcribe", json={"text": "hello assistant"})
    assert result.status_code == 200
    assert result.json()["text"] == "hello assistant"


def test_observability_summary_and_ui(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWCASE_DB_PATH", str(tmp_path / "showcase.db"))

    memory_store = importlib.import_module("src.memory.store")
    importlib.reload(memory_store)
    app_module = importlib.import_module("src.api.app")
    importlib.reload(app_module)

    client = TestClient(app_module.app)

    summary = client.get("/observability/summary")
    assert summary.status_code == 200
    assert "metrics" in summary.json()

    ui = client.get("/ui")
    assert ui.status_code == 200
    assert "Public Showcase AI Assistant Dashboard" in ui.text


def test_optional_token_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWCASE_DB_PATH", str(tmp_path / "showcase.db"))
    monkeypatch.setenv("SHOWCASE_API_TOKEN", "demo-token")

    config_module = importlib.import_module("src.config")
    importlib.reload(config_module)
    auth_module = importlib.import_module("src.api.auth")
    importlib.reload(auth_module)
    memory_store = importlib.import_module("src.memory.store")
    importlib.reload(memory_store)
    app_module = importlib.import_module("src.api.app")
    importlib.reload(app_module)

    client = TestClient(app_module.app)

    unauthorized = client.get("/dashboard")
    assert unauthorized.status_code == 401

    authorized = client.get("/dashboard", headers={"x-api-token": "demo-token"})
    assert authorized.status_code == 200
