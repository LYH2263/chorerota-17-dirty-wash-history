"""历史格回洗模块：显式改写已生成周里的异常格（唯一合法途径）。

拍板：历史格只有两种归宿——被本模块显式改写，或保持只读异常（不操作即
保持，无需第三态）。现行回洗永不触碰这里。改写按周全有或全无：
  - 任务仍脏/负权 -> 409 task_unfit，须先对任务做现行回洗；
  - 成员已恢复干净 -> 仅清除 anomaly 闩锁，格子内容不动；
  - 成员仍不可用   -> 确定性改派给本周负载最轻的干净在岗成员。
"""
from fastapi import APIRouter, HTTPException

from app.db import connect
from app.engines.quality import plan_rewrites

router = APIRouter()


@router.post("/api/weeks/{week_id}/backwash")
def backwash_week_cells(week_id: int):
    c = connect()
    week = c.execute("SELECT * FROM weeks WHERE id=?", (week_id,)).fetchone()
    if not week:
        c.close()
        raise HTTPException(404, "week not found")
    cells = [
        dict(r)
        for r in c.execute(
            "SELECT id,day,task_id,member_id,anomaly FROM assignments WHERE week_id=? ORDER BY id",
            (week_id,),
        )
    ]
    members = {r["id"]: dict(r) for r in c.execute("SELECT * FROM members")}
    tasks = {r["id"]: dict(r) for r in c.execute("SELECT * FROM tasks")}
    updates, err = plan_rewrites(cells, members, tasks)
    if err:
        c.close()
        raise HTTPException(409, err)
    for u in updates:
        c.execute(
            "UPDATE assignments SET member_id=?, anomaly=0 WHERE id=?",
            (u["member_id"], u["id"]),
        )
    c.commit()
    c.close()
    return {"rewritten": len(updates), "cells": updates}
