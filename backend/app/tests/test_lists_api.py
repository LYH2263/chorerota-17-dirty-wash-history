"""列表模块测例：dirty 与负权项照常展示；看板格带 anomaly 闩锁标记。"""
from app.tests.conftest import board, generate


def test_members_list_shows_dirty_and_inactive(client):
    rows = client.get("/api/members").json()
    ghost = next(r for r in rows if r["name"] == "幽灵成员")
    assert ghost["data_quality"] == "dirty" and ghost["active"] == 0
    assert len(rows) == 4  # 不过滤，全部展示


def test_tasks_list_shows_dirty_and_negative_weight(client):
    rows = client.get("/api/tasks").json()
    bad = next(r for r in rows if r["title"] == "负权重任务")
    assert bad["data_quality"] == "dirty" and bad["weight"] == -1
    assert len(rows) == 4


def test_board_cells_carry_anomaly_flag(client):
    generate(client)
    b = board(client)
    assert b["assignments"], "生成后应有格子"
    assert all(a["anomaly"] == 0 for a in b["assignments"])
    client.post("/api/members/2/isolate", json={})
    flagged = [a for a in board(client)["assignments"] if a["anomaly"] == 1]
    assert flagged and all(a["member_id"] == 2 for a in flagged)
