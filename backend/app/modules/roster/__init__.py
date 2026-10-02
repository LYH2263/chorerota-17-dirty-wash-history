"""列表模块：成员/任务/周/看板的只读与录入。

列表如实展示 dirty 与负权项（不过滤）；看板格子带 anomaly 闩锁标记，
异常格只读展示，改写只能走 backwash_history 模块。
"""
from fastapi import APIRouter, HTTPException

from app.db import connect

router = APIRouter()


@router.get("/api/members")
def list_members():
    c = connect()
    rows = [dict(r) for r in c.execute("SELECT * FROM members")]
    c.close()
    return rows


@router.post("/api/members")
def add_member(body: dict):
    c = connect()
    cur = c.execute(
        "INSERT INTO members(name,active,data_quality) VALUES (?,?,?)",
        (body.get("name", "未命名"), int(body.get("active", 1)), body.get("data_quality", "clean")),
    )
    c.commit()
    mid = cur.lastrowid
    c.close()
    return {"id": mid}


@router.get("/api/tasks")
def list_tasks():
    c = connect()
    rows = [dict(r) for r in c.execute("SELECT * FROM tasks")]
    c.close()
    return rows


@router.post("/api/tasks")
def add_task(body: dict):
    c = connect()
    cur = c.execute(
        "INSERT INTO tasks(title,weight,data_quality) VALUES (?,?,?)",
        (body.get("title", "任务"), int(body.get("weight", 1)), body.get("data_quality", "clean")),
    )
    c.commit()
    tid = cur.lastrowid
    c.close()
    return {"id": tid}


@router.get("/api/weeks")
def list_weeks():
    c = connect()
    rows = [dict(r) for r in c.execute("SELECT * FROM weeks")]
    c.close()
    return rows


@router.get("/api/weeks/{week_id}/board")
def week_board(week_id: int):
    c = connect()
    week = c.execute("SELECT * FROM weeks WHERE id=?", (week_id,)).fetchone()
    if not week:
        c.close()
        raise HTTPException(404, "week not found")
    assigns = [dict(r) for r in c.execute("SELECT * FROM assignments WHERE week_id=?", (week_id,))]
    members = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM members")}
    tasks = {r["id"]: r["title"] for r in c.execute("SELECT id,title FROM tasks")}
    c.close()
    for a in assigns:
        a["member_name"] = members.get(a["member_id"], "?")
        a["task_title"] = tasks.get(a["task_id"], "?")
    return {"week": dict(week), "assignments": assigns}
