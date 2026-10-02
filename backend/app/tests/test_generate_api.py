"""生成模块测例：隔离 dirty/负权实体；现行回洗后仅新生成可纳入。"""
from app.tests.conftest import generate


def test_generate_excludes_dirty_and_negative_weight(client):
    res = generate(client)
    assert res["count"] == 21
    assert {s["member_id"] for s in res["slots"]} == {1, 2, 3}
    assert {s["task_id"] for s in res["slots"]} == {1, 2, 3}
    assert res["skipped"] == {"members": [4], "tasks": [4]}


def test_generate_excludes_newly_isolated_entity(client):
    generate(client)
    client.post("/api/members/2/isolate", json={})
    client.post("/api/tasks/3/isolate", json={"weight": 0})
    res = generate(client)
    assert {s["member_id"] for s in res["slots"]} == {1, 3}
    assert {s["task_id"] for s in res["slots"]} == {1, 2}
    assert res["skipped"] == {"members": [2, 4], "tasks": [3, 4]}


def test_backwashed_entity_only_enters_new_generations(client):
    generate(client)
    client.post("/api/members/2/isolate", json={})
    res = generate(client)
    assert 2 not in {s["member_id"] for s in res["slots"]}
    r = client.post("/api/members/2/backwash", json={})
    assert r.status_code == 200
    res = generate(client)  # 回洗后的第一次新生成即可纳入
    assert 2 in {s["member_id"] for s in res["slots"]}
