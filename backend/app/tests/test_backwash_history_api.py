"""历史格回洗模块测例：显式改写异常格；不改写则保持只读异常。"""
from app.tests.conftest import board, generate


def test_rewrite_reassigns_still_unfit_member(client):
    generate(client)
    client.post("/api/members/2/isolate", json={})
    r = client.post("/api/weeks/1/backwash")
    assert r.status_code == 200
    assert r.json()["rewritten"] == 7
    cells = board(client)["assignments"]
    assert all(a["anomaly"] == 0 for a in cells)
    moved = [a for a in cells if a["task_id"] == 2]
    assert all(a["member_id"] in (1, 3) for a in moved)  # 改派给干净在岗成员
    assert {a["member_id"] for a in moved} == {1, 3}  # 负载均衡到两人


def test_rewrite_after_reclean_keeps_assignee(client):
    generate(client)
    client.post("/api/members/2/isolate", json={})
    client.post("/api/members/2/backwash", json={})  # 现行回洗只清实体
    assert sum(1 for a in board(client)["assignments"] if a["anomaly"]) == 7
    r = client.post("/api/weeks/1/backwash")
    assert r.json()["rewritten"] == 7
    cells = board(client)["assignments"]
    assert all(a["anomaly"] == 0 for a in cells)
    assert all(a["member_id"] == 2 for a in cells if a["task_id"] == 2)  # 格子内容未被改派


def test_rewrite_blocked_until_task_backwashed(client):
    generate(client)
    client.post("/api/tasks/2/isolate", json={})
    r = client.post("/api/weeks/1/backwash")
    assert r.status_code == 409 and r.json()["detail"]["error"] == "task_unfit"
    assert sum(1 for a in board(client)["assignments"] if a["anomaly"]) == 7  # 全有或全无
    client.post("/api/tasks/2/backwash", json={})  # 先走现行回洗
    r = client.post("/api/weeks/1/backwash")
    assert r.status_code == 200 and r.json()["rewritten"] == 7
    assert all(a["anomaly"] == 0 for a in board(client)["assignments"])


def test_rewrite_without_anomaly_is_noop(client):
    generate(client)
    r = client.post("/api/weeks/1/backwash")
    assert r.status_code == 200 and r.json()["rewritten"] == 0


def test_rewrite_unknown_week_404(client):
    assert client.post("/api/weeks/99/backwash").status_code == 404
