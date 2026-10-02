"""对调模块测例：异常格申请/确认均失败，且对调表不增成功行。"""
from app.tests.conftest import board, generate


def _cell(client, day, task):
    return next(
        a for a in board(client)["assignments"] if a["day"] == day and a["task_id"] == task
    )


def test_swap_happy_path_still_works(client):
    generate(client)
    r = client.post("/api/weeks/1/swaps", json={"a_day": 0, "a_task": 1, "b_day": 0, "b_task": 2})
    assert r.status_code == 200
    sid = r.json()["id"]
    r = client.post(f"/api/swaps/{sid}/confirm")
    assert r.status_code == 200
    assert _cell(client, 0, 1)["member_id"] == 2
    assert _cell(client, 0, 2)["member_id"] == 1
    assert client.get("/api/swaps").json()[0]["status"] == "confirmed"


def test_request_on_anomaly_cell_fails_without_row(client):
    generate(client)
    client.post("/api/members/2/isolate", json={})
    before = len(client.get("/api/swaps").json())
    r = client.post("/api/weeks/1/swaps", json={"a_day": 0, "a_task": 2, "b_day": 0, "b_task": 3})
    assert r.status_code == 400
    assert r.json()["detail"]["reason"] == "anomaly_cell"
    assert len(client.get("/api/swaps").json()) == before  # 不增成功行（一行都不增）


def test_confirm_after_isolation_fails_and_marks_failed(client):
    generate(client)
    r = client.post("/api/weeks/1/swaps", json={"a_day": 0, "a_task": 1, "b_day": 0, "b_task": 2})
    sid = r.json()["id"]
    client.post("/api/members/1/isolate", json={})  # 申请后才转异常
    r = client.post(f"/api/swaps/{sid}/confirm")
    assert r.status_code == 400
    assert r.json()["detail"]["reason"] == "anomaly_cell"
    row = next(s for s in client.get("/api/swaps").json() if s["id"] == sid)
    assert row["status"] == "failed"  # 不是成功行
    assert _cell(client, 0, 1)["member_id"] == 1  # 格子未被改动
    assert _cell(client, 0, 2)["member_id"] == 2
    # failed 行不可再确认
    assert client.post(f"/api/swaps/{sid}/confirm").status_code == 400


def test_swap_legality_checks_still_apply(client):
    generate(client)
    r = client.post("/api/weeks/1/swaps", json={"a_day": 0, "a_task": 1, "b_day": 1, "b_task": 1})
    assert r.status_code == 400 and r.json()["detail"] == "same_assignee"
