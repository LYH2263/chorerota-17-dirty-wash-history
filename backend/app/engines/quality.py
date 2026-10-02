"""Data-quality rules: entity fitness, cell anomaly, historical rewrite planning.

Anomaly is a *latched* property of an assignment cell (assignments.anomaly),
stamped by isolation when an entity turns unfit. Current-backwash cleans the
entity only and never clears latched cells; history-backwash is the single
explicit action that rewrites them. These functions are pure so the policy is
testable without a database.
"""


def member_fit(member: dict | None) -> bool:
    """A member may enter new generation/swaps only when clean and active."""
    return (
        bool(member)
        and member.get("data_quality") == "clean"
        and int(member.get("active", 0)) == 1
    )


def task_fit(task: dict | None) -> bool:
    """A task may enter new generation/swaps only when clean with weight > 0."""
    return (
        bool(task)
        and task.get("data_quality") == "clean"
        and int(task.get("weight", 0)) > 0
    )


def cell_anomaly_reasons(member: dict | None, task: dict | None) -> list[str]:
    """Why a cell referencing these entities is anomalous (empty = healthy)."""
    reasons = []
    if not member_fit(member):
        reasons.append("member_unfit")
    if not task_fit(task):
        reasons.append("task_unfit")
    return reasons


def plan_rewrites(
    cells: list[dict], members: dict[int, dict], tasks: dict[int, dict]
) -> tuple[list[dict] | None, dict | None]:
    """Plan the historical-cell backwash for one week, all-or-nothing.

    cells: every assignment row of the week as dicts with
        id/day/task_id/member_id/anomaly. members/tasks: id -> entity row.

    Returns (updates, None) where updates = [{"id": cell_id, "member_id": ...}]
    for each anomalous cell (flag is cleared by the caller), or (None, error)
    with error = {"error": "task_unfit"|"no_clean_member", ...} and no update
    planned at all.

    Policy per anomalous cell:
      - task still unfit        -> abort the whole plan (task_unfit); the task
                                   must go through current-backwash first.
      - member fit again        -> keep the assignee, only clear the flag.
      - member still unfit      -> reassign to the fit member with the fewest
                                   cells in this week (ties: lowest id).
    """
    anomalous = sorted((c for c in cells if c.get("anomaly")), key=lambda c: c["id"])
    unfit_tasks = sorted(
        {c["task_id"] for c in anomalous if not task_fit(tasks.get(c["task_id"]))}
    )
    if unfit_tasks:
        return None, {"error": "task_unfit", "task_ids": unfit_tasks}

    fit_ids = sorted(mid for mid, m in members.items() if member_fit(m))
    if any(not member_fit(members.get(c["member_id"])) for c in anomalous) and not fit_ids:
        return None, {"error": "no_clean_member"}

    load = {mid: 0 for mid in fit_ids}
    for c in cells:
        if not c.get("anomaly") and c["member_id"] in load:
            load[c["member_id"]] += 1

    updates = []
    for c in anomalous:
        mid = c["member_id"]
        if member_fit(members.get(mid)):
            updates.append({"id": c["id"], "member_id": mid})
            if mid in load:
                load[mid] += 1
        else:
            pick = min(fit_ids, key=lambda m: (load[m], m))
            updates.append({"id": c["id"], "member_id": pick})
            load[pick] += 1
    return updates, None
