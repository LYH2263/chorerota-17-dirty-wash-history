import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """每个用例独立 sqlite 库（种子数据），并触发 startup 建表。"""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with TestClient(app) as c:
        yield c


def generate(client, week_id=1, days=7):
    r = client.post(f"/api/weeks/{week_id}/generate", json={"days": days})
    assert r.status_code == 200, r.text
    return r.json()


def board(client, week_id=1):
    r = client.get(f"/api/weeks/{week_id}/board")
    assert r.status_code == 200, r.text
    return r.json()
