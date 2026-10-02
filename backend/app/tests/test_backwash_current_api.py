"""现行回洗模块测例：隔离闩锁异常格；回洗只清实体、绝不静默改历史格。"""
from app.tests.conftest import board, generate


def test_isolate_member_latches_existing_cells(client):
    generate(client)
    r = client.post("/api/members/2/isolate", json={})
    assert r.status_code == 200 and r.json()["latched_cells"] == 7  # 成员2 每天一格任务2
    cells = board(client)["assignments"]
    assert sum(1 for a in cells if a["anomaly"] == 1) == 7
    assert all(a["anomaly"] == 1 for a in cells if a["member_id"] == 2)


def test_isolate_task_by_negative_weight_latches(client):
    generate(client)
    r = client.post("/api/tasks/3/isolate", json={"weight": -2})
    assert r.json()["latched_cells"] == 7
    cells = board(client)["assignments"]
    assert all(a["anomaly"] == 1 for a in cells if a["task_id"] == 3)


def test_backwash_does_not_touch_historical_cells(client):
    generate(client)
    client.post("/api/members/2/isolate", json={})
    r = client.post("/api/members/2/backwash", json={})
    assert r.status_code == 200
    # 实体已干净，但历史格保持闩锁，数量显式上报
    assert r.json()["residual_anomaly_cells"] == 7
    cells = board(client)["assignments"]
    assert sum(1 for a in cells if a["anomaly"] == 1) == 7
    m2 = next(m for m in client.get("/api/members").json() if m["id"] == 2)
    assert m2["data_quality"] == "clean"


def test_backwash_task_requires_positive_weight(client):
    r = client.post("/api/tasks/4/backwash", json={})  # 负权重任务不修正权重 -> 400
    assert r.status_code == 400
    t4 = next(t for t in client.get("/api/tasks").json() if t["id"] == 4)
    assert t4["data_quality"] == "dirty"  # 校验失败整体回滚
    r = client.post("/api/tasks/4/backwash", json={"weight": 2})
    assert r.status_code == 200
    t4 = next(t for t in client.get("/api/tasks").json() if t["id"] == 4)
    assert t4["data_quality"] == "clean" and t4["weight"] == 2


def test_isolate_unknown_entity_404(client):
    assert client.post("/api/members/99/isolate", json={}).status_code == 404
    assert client.post("/api/tasks/99/backwash", json={"weight": 1}).status_code == 404
