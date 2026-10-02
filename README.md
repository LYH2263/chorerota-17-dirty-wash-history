# Chorerota · 家庭值日轮转

底座：成员+任务 → round-robin 生成周表 → 申请对调 → 确认改表。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5100 |
| API | 10100 |

```bash
docker compose up --build
pytest backend/app/tests
```

种子含 clean/dirty。0-1 空桩：`streak_badge` / `skip_week` / `chore_photo`。

## 脏数据隔离与回洗

成员/任务列表**照常展示** dirty 与负权项；生成与对调**不得引用**它们。
异常是格级闩锁（`assignments.anomaly`）：隔离动作把既有格子闩上异常，
看板保持异常标记、只读展示。

五路分模块（`backend/app/modules/`）：

| 模块 | 路由 | 职责 |
| --- | --- | --- |
| `roster` | 列表 | members/tasks/weeks/board 查询与录入，如实展示脏数据 |
| `generate` | 生成 | 仅用 clean+在岗成员、clean+正权任务落位；`skipped` 显式列出被隔离者 |
| `backwash_current` | 现行回洗 | `POST /members/{id}/isolate|backwash`、`POST /tasks/{id}/isolate|backwash`；隔离闩锁历史格，回洗只清实体/修权重 |
| `backwash_history` | 历史格回洗 | `POST /weeks/{id}/backwash` 显式改写异常格（全有或全无） |
| `swaps` | 对调 | 涉异常格的申请/确认 400，对调表不增成功行（确认失败标 `failed`） |

**拍板（两种策略取舍）**：历史格只有两种归宿——被历史格回洗**显式改写**，
或**保持只读异常**（不操作即保持）。不设"已确认异常"第三态：它功能上
与只读异常等价（照样禁对调），却多一个状态机分支。现行回洗**禁止静默
改历史格**——回洗后历史格保持闩锁，响应 `residual_anomaly_cells` 显式
上报数量，须另走历史格回洗。

历史格回洗规则：

- 任务仍 dirty/负权 → `409 task_unfit`，须先对该任务做现行回洗；
- 成员已恢复干净 → 仅清闩锁，格子内容不动；
- 成员仍不可用 → 确定性改派给本周负载最轻的 clean+在岗成员（同负载取小 id）。

测例：`app/tests/test_quality.py`（引擎）+ `test_lists_api / test_generate_api /
test_backwash_current_api / test_backwash_history_api / test_swaps_api`（五路 API）。
