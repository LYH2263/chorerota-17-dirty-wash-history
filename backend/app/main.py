from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import seed
from app.db import connect
from app.modules import backwash_current, backwash_history, generate, roster, swaps

app = FastAPI(title="Chorerota", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 五路分模块：列表 / 生成 / 现行回洗 / 历史格回洗 / 对调
app.include_router(roster.router)
app.include_router(generate.router)
app.include_router(backwash_current.router)
app.include_router(backwash_history.router)
app.include_router(swaps.router)


@app.on_event("startup")
def _startup():
    seed.init_db()


@app.get("/api/health")
def health():
    return {"ok": True, "project": "chorerota"}


@app.get("/api/settings")
def get_settings():
    c = connect()
    rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}
    c.close()
    return rows


@app.put("/api/settings")
def put_settings(body: dict):
    c = connect()
    for k, v in body.items():
        c.execute(
            "INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (k, str(v)),
        )
    c.commit()
    c.close()
    return {"ok": True}
