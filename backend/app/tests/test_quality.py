"""引擎层纯函数测例：实体适配、异常判定、历史格改写计划。"""
from app.engines.quality import (
    cell_anomaly_reasons,
    member_fit,
    plan_rewrites,
    task_fit,
)

CLEAN_MEMBER = {"id": 1, "active": 1, "data_quality": "clean"}
CLEAN_TASK = {"id": 10, "weight": 1, "data_quality": "clean"}


def test_member_fit_truth_table():
    assert member_fit(CLEAN_MEMBER)
    assert not member_fit({**CLEAN_MEMBER, "data_quality": "dirty"})
    assert not member_fit({**CLEAN_MEMBER, "active": 0})
    assert not member_fit(None)


def test_task_fit_truth_table():
    assert task_fit(CLEAN_TASK)
    assert not task_fit({**CLEAN_TASK, "weight": 0})
    assert not task_fit({**CLEAN_TASK, "weight": -1})
    assert not task_fit({**CLEAN_TASK, "data_quality": "dirty"})
    assert not task_fit(None)


def test_cell_anomaly_reasons():
    assert cell_anomaly_reasons(CLEAN_MEMBER, CLEAN_TASK) == []
    assert cell_anomaly_reasons(None, CLEAN_TASK) == ["member_unfit"]
    assert cell_anomaly_reasons(CLEAN_MEMBER, {**CLEAN_TASK, "weight": -1}) == ["task_unfit"]
    assert cell_anomaly_reasons(None, None) == ["member_unfit", "task_unfit"]


def _cells():
    # 两格异常（id 2、3），一格正常（id 1，成员 1）
    return [
        {"id": 1, "day": 0, "task_id": 10, "member_id": 1, "anomaly": 0},
        {"id": 2, "day": 1, "task_id": 10, "member_id": 2, "anomaly": 1},
        {"id": 3, "day": 2, "task_id": 10, "member_id": 3, "anomaly": 1},
    ]


def test_plan_rewrites_recleaned_member_keeps_cell():
    members = {1: CLEAN_MEMBER, 2: {**CLEAN_MEMBER, "id": 2}, 3: {**CLEAN_MEMBER, "id": 3}}
    updates, err = plan_rewrites(_cells(), members, {10: CLEAN_TASK})
    assert err is None
    # 成员已恢复干净：只清闩锁，不改派
    assert updates == [{"id": 2, "member_id": 2}, {"id": 3, "member_id": 3}]


def test_plan_rewrites_unfit_member_goes_to_least_loaded_fit():
    members = {
        1: CLEAN_MEMBER,
        2: {**CLEAN_MEMBER, "id": 2, "data_quality": "dirty"},
        3: {**CLEAN_MEMBER, "id": 3, "active": 0},
        4: {**CLEAN_MEMBER, "id": 4},
    }
    updates, err = plan_rewrites(_cells(), members, {10: CLEAN_TASK})
    assert err is None
    # 干净在岗者只有 1、4；成员 1 已有 1 格 -> 两格都改派，先 4 后 1 均衡
    assert updates == [{"id": 2, "member_id": 4}, {"id": 3, "member_id": 1}]


def test_plan_rewrites_aborts_on_unfit_task():
    members = {1: CLEAN_MEMBER, 2: {**CLEAN_MEMBER, "id": 2}, 3: {**CLEAN_MEMBER, "id": 3}}
    updates, err = plan_rewrites(_cells(), members, {10: {**CLEAN_TASK, "data_quality": "dirty"}})
    assert updates is None
    assert err["error"] == "task_unfit" and err["task_ids"] == [10]


def test_plan_rewrites_no_clean_member():
    members = {
        1: {**CLEAN_MEMBER, "data_quality": "dirty"},
        2: {**CLEAN_MEMBER, "id": 2, "data_quality": "dirty"},
        3: {**CLEAN_MEMBER, "id": 3, "data_quality": "dirty"},
    }
    updates, err = plan_rewrites(_cells(), members, {10: CLEAN_TASK})
    assert updates is None
    assert err["error"] == "no_clean_member"


def test_plan_rewrites_no_anomaly_is_noop():
    cells = [dict(c, anomaly=0) for c in _cells()]
    updates, err = plan_rewrites(cells, {1: CLEAN_MEMBER}, {10: CLEAN_TASK})
    assert err is None and updates == []
