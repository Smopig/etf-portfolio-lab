"""API-layer tests for the one-click data refresh endpoints.

Uses monkeypatch to stub out app.services.refresh_service so no real
fetch / background thread / network activity occurs.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.main import app


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test_data_refresh.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


IDLE_STATE = {
    "running": False,
    "phase": "idle",
    "total": 0,
    "processed": 0,
    "succeeded": 0,
    "failed": 0,
    "started_at": None,
    "finished_at": None,
    "message": "",
}

RUNNING_STATE = {
    "running": True,
    "phase": "listing",
    "total": 0,
    "processed": 0,
    "succeeded": 0,
    "failed": 0,
    "started_at": "2026-06-13T00:00:00",
    "finished_at": None,
    "message": "抓取 ETF 清單中...",
}


def test_post_refresh_started(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.data_refresh.refresh_service.start_refresh",
        lambda **kwargs: ("started", dict(RUNNING_STATE)),
    )

    resp = client.post("/api/data/refresh", json={})
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["status"] == "started"
    assert body["running"] is True
    assert body["phase"] == "listing"


def test_post_refresh_already_running(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.data_refresh.refresh_service.start_refresh",
        lambda **kwargs: ("already_running", dict(RUNNING_STATE)),
    )

    resp = client.post("/api/data/refresh", json={"prices": False, "limit": 5})
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["status"] == "already_running"


def test_get_refresh_status(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.data_refresh.refresh_service.get_status",
        lambda: dict(IDLE_STATE),
    )

    resp = client.get("/api/data/refresh/status")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["running"] is False
    assert body["phase"] == "idle"
    for key in IDLE_STATE:
        assert key in body
