"""生成模块：仅用干净实体落位新周表。

隔离规则：成员须 clean 且在岗，任务须 clean 且权重 > 0；dirty/负权项
永不进入生成。新格 anomaly=0；被隔离的实体在响应的 skipped 中显式列出。
现行回洗过的实体从这里（且仅从这里）重新进入新周表。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import connect
from app.engines.rota import build_week_slots

router = APIRouter()


class GenBody(BaseModel):
    days: int = 7


@router.post("/api/weeks/{week_id}/generate")
def generate(week_id: int, body: GenBody = GenBody()):
    c = connect()
    week = c.execute("SELECT * FROM weeks WHERE id=?", (week_id,)).fetchone()
    if not week:
        c.close()
        raise HTTPException(404, "week not found")
    mids = [
        r["id"]
        for r in c.execute(
            "SELECT id FROM members WHERE active=1 AND data_quality='clean' ORDER BY id"
        )
    ]
    tids = [
        r["id"]
        for r in c.execute(
            "SELECT id FROM tasks WHERE data_quality='clean' AND weight>0 ORDER BY id"
        )
    ]
    skipped = {
        "members": [
            r["id"]
            for r in c.execute(
                "SELECT id FROM members WHERE NOT (active=1 AND data_quality='clean') ORDER BY id"
            )
        ],
        "tasks": [
            r["id"]
            for r in c.execute(
                "SELECT id FROM tasks WHERE NOT (data_quality='clean' AND weight>0) ORDER BY id"
            )
        ],
    }
    slots = build_week_slots(mids, tids, days=body.days)
    c.execute("DELETE FROM assignments WHERE week_id=?", (week_id,))
    for s in slots:
        c.execute(
            "INSERT INTO assignments(week_id,day,task_id,member_id,anomaly) VALUES (?,?,?,?,0)",
            (week_id, s["day"], s["task_id"], s["member_id"]),
        )
    c.execute("UPDATE weeks SET status='ready' WHERE id=?", (week_id,))
    c.commit()
    c.close()
    return {"count": len(slots), "slots": slots, "skipped": skipped}
