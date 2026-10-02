"""对调模块：申请/列表/确认，全程对异常格设卡。

涉及 anomaly=1 格子的申请直接 400，且不在对调表落任何行；确认时若格子
已转异常（申请后才被隔离），同样 400 并把该 pending 行标 failed——
对调表永不因异常格增加成功行。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import connect
from app.engines.rota import apply_swap, swap_legal

router = APIRouter()


class SwapBody(BaseModel):
    a_day: int
    a_task: int
    b_day: int
    b_task: int
    note: str = ""


def _anomalous_cells(c, week_id, cells):
    """Return the (day, task) pairs among cells that are latched anomalous."""
    bad = []
    for day, task in cells:
        row = c.execute(
            "SELECT anomaly FROM assignments WHERE week_id=? AND day=? AND task_id=?",
            (week_id, day, task),
        ).fetchone()
        if row and row["anomaly"]:
            bad.append({"day": day, "task_id": task})
    return bad


@router.post("/api/weeks/{week_id}/swaps")
def request_swap(week_id: int, body: SwapBody):
    c = connect()
    assigns = [
        dict(r)
        for r in c.execute(
            "SELECT day,task_id,member_id FROM assignments WHERE week_id=?", (week_id,)
        )
    ]
    check = swap_legal(assigns, body.a_day, body.a_task, body.b_day, body.b_task)
    if not check["ok"]:
        c.close()
        raise HTTPException(400, check["reason"])
    bad = _anomalous_cells(
        c, week_id, [(body.a_day, body.a_task), (body.b_day, body.b_task)]
    )
    if bad:
        c.close()
        raise HTTPException(400, {"reason": "anomaly_cell", "cells": bad})
    cur = c.execute(
        "INSERT INTO swap_requests(week_id,a_day,a_task,b_day,b_task,status,note) VALUES (?,?,?,?,?,?,?)",
        (week_id, body.a_day, body.a_task, body.b_day, body.b_task, "pending", body.note),
    )
    c.commit()
    sid = cur.lastrowid
    c.close()
    return {"id": sid, "status": "pending", **check}


@router.get("/api/swaps")
def list_swaps():
    c = connect()
    rows = [dict(r) for r in c.execute("SELECT * FROM swap_requests ORDER BY id DESC")]
    c.close()
    return rows


@router.post("/api/swaps/{swap_id}/confirm")
def confirm_swap(swap_id: int):
    c = connect()
    sw = c.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    if not sw:
        c.close()
        raise HTTPException(404, "swap not found")
    if sw["status"] != "pending":
        c.close()
        raise HTTPException(400, "not_pending")
    bad = _anomalous_cells(c, sw["week_id"], [(sw["a_day"], sw["a_task"]), (sw["b_day"], sw["b_task"])])
    if bad:
        # 确认失败：pending 行标 failed（非成功行），格子不动。
        c.execute("UPDATE swap_requests SET status='failed' WHERE id=?", (swap_id,))
        c.commit()
        c.close()
        raise HTTPException(400, {"reason": "anomaly_cell", "cells": bad})
    assigns = [
        dict(r)
        for r in c.execute(
            "SELECT id,day,task_id,member_id FROM assignments WHERE week_id=?",
            (sw["week_id"],),
        )
    ]
    slots = [{"day": a["day"], "task_id": a["task_id"], "member_id": a["member_id"]} for a in assigns]
    try:
        new_slots = apply_swap(slots, sw["a_day"], sw["a_task"], sw["b_day"], sw["b_task"])
    except ValueError as e:
        c.close()
        raise HTTPException(400, str(e))
    for a, s in zip(assigns, new_slots):
        c.execute("UPDATE assignments SET member_id=? WHERE id=?", (s["member_id"], a["id"]))
    c.execute("UPDATE swap_requests SET status='confirmed' WHERE id=?", (swap_id,))
    c.commit()
    c.close()
    return {"ok": True, "swap_id": swap_id}
