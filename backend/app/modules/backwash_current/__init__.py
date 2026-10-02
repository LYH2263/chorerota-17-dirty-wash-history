"""现行回洗模块：实体的隔离与回洗（只动实体，绝不动历史格）。

隔离 isolate：把实体标 dirty / 停用 / 负权，并把既有格子闩上 anomaly=1
——这是显式隔离动作，闩锁即其职责。
现行回洗 backwash：把实体标 clean / 修正权重，使其仅对「新生成」可用；
已生成周的历史格保持 anomaly 闩锁不动（禁止静默改历史格），响应里的
residual_anomaly_cells 显式报告仍挂异常的历史格数量，须另走
backwash_history 模块显式改写。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import connect
from app.engines.quality import member_fit, task_fit

router = APIRouter()


def _get_or_404(c, table, row_id):
    row = c.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone()
    if not row:
        c.close()
        raise HTTPException(404, f"{table} row not found")
    return dict(row)


def _latched_cells(c, column, row_id):
    return c.execute(
        f"SELECT COUNT(*) n FROM assignments WHERE anomaly=1 AND {column}=?", (row_id,)
    ).fetchone()["n"]


def _latch_cells(c, column, row_id):
    cur = c.execute(f"UPDATE assignments SET anomaly=1 WHERE {column}=?", (row_id,))
    return cur.rowcount


class MemberIsolate(BaseModel):
    data_quality: str = "dirty"
    active: int | None = None


class MemberBackwash(BaseModel):
    data_quality: str = "clean"
    active: int | None = None


@router.post("/api/members/{member_id}/isolate")
def isolate_member(member_id: int, body: MemberIsolate = MemberIsolate()):
    c = connect()
    _get_or_404(c, "members", member_id)
    c.execute("UPDATE members SET data_quality=? WHERE id=?", (body.data_quality, member_id))
    if body.active is not None:
        c.execute("UPDATE members SET active=? WHERE id=?", (int(body.active), member_id))
    latched = 0
    if not member_fit(_get_or_404(c, "members", member_id)):
        latched = _latch_cells(c, "member_id", member_id)
    c.commit()
    c.close()
    return {"id": member_id, "latched_cells": latched}


@router.post("/api/members/{member_id}/backwash")
def backwash_member(member_id: int, body: MemberBackwash = MemberBackwash()):
    c = connect()
    _get_or_404(c, "members", member_id)
    c.execute("UPDATE members SET data_quality=? WHERE id=?", (body.data_quality, member_id))
    if body.active is not None:
        c.execute("UPDATE members SET active=? WHERE id=?", (int(body.active), member_id))
    if not member_fit(_get_or_404(c, "members", member_id)):
        c.close()
        raise HTTPException(400, "backwash_must_leave_member_fit")
    residual = _latched_cells(c, "member_id", member_id)
    c.commit()
    c.close()
    # 只清实体；历史格 anomaly 保持闩锁，数量显式上报。
    return {"id": member_id, "residual_anomaly_cells": residual}


class TaskIsolate(BaseModel):
    data_quality: str = "dirty"
    weight: int | None = None


class TaskBackwash(BaseModel):
    data_quality: str = "clean"
    weight: int | None = None


@router.post("/api/tasks/{task_id}/isolate")
def isolate_task(task_id: int, body: TaskIsolate = TaskIsolate()):
    c = connect()
    _get_or_404(c, "tasks", task_id)
    c.execute("UPDATE tasks SET data_quality=? WHERE id=?", (body.data_quality, task_id))
    if body.weight is not None:
        c.execute("UPDATE tasks SET weight=? WHERE id=?", (int(body.weight), task_id))
    latched = 0
    if not task_fit(_get_or_404(c, "tasks", task_id)):
        latched = _latch_cells(c, "task_id", task_id)
    c.commit()
    c.close()
    return {"id": task_id, "latched_cells": latched}


@router.post("/api/tasks/{task_id}/backwash")
def backwash_task(task_id: int, body: TaskBackwash = TaskBackwash()):
    c = connect()
    _get_or_404(c, "tasks", task_id)
    c.execute("UPDATE tasks SET data_quality=? WHERE id=?", (body.data_quality, task_id))
    if body.weight is not None:
        c.execute("UPDATE tasks SET weight=? WHERE id=?", (int(body.weight), task_id))
    if not task_fit(_get_or_404(c, "tasks", task_id)):
        c.close()
        raise HTTPException(400, "backwash_must_leave_task_fit_weight_positive")
    residual = _latched_cells(c, "task_id", task_id)
    c.commit()
    c.close()
    # 只清实体、修正权重；历史格 anomaly 保持闩锁，数量显式上报。
    return {"id": task_id, "residual_anomaly_cells": residual}
