from __future__ import annotations

import time
from datetime import datetime, UTC
from typing import Any, List, Dict
from audit.log import log_event
from policy.capabilities import issue_token

from .execute_step import execute_step
from .plan_hash import compute_plan_hash
from .plan_validator import validate_plan
from .plan_store import (
    load_approved_plan,
    mark_plan_approved,
    plan_has_executed,
    plan_is_approved,
    store_pending_plan,
    write_executed_marker,
    overwrite_executed_marker,
    write_failure_envelope,
    write_summary,
)


TOKEN_ACTION_BY_TOOL = {
    "TEST_RUN": "CMD_RUN",
    "GIT_RUN": "GIT_RUN",
    "PATCH_APPLY": "FS_WRITE_PATCH",
}

MAX_STEPS_PER_EXECUTION = 25
MAX_EXECUTION_SECONDS = 120


# -----------------------------------------------------------------------------
# Plan lifecycle (submit / approve)
# -----------------------------------------------------------------------------

def submit_plan(plan):
    validate_plan(plan)
    plan_hash = compute_plan_hash(plan)
    store_pending_plan(plan_hash, plan)

    log_event(
        "PLAN_CREATED",
        {
            "plan_hash": plan_hash,
            "steps": len(plan.steps),
            "status": "PENDING_APPROVAL",
        },
    )

    return {
        "plan_hash": plan_hash,
        "steps": len(plan.steps),
        "status": "PENDING_APPROVAL",
    }


def approve_plan(plan_hash: str):
    mark_plan_approved(plan_hash)

    log_event(
        "PLAN_APPROVED",
        {
            "plan_hash": plan_hash,
        },
    )

    return {
        "plan_hash": plan_hash,
        "status": "APPROVED",
    }


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_tx_id(plan_hash: str) -> str:
    return f"{plan_hash[:12]}-{int(time.time())}"


def _issue_step_token(step):
    action = TOKEN_ACTION_BY_TOOL.get(step.tool)
    if not action:
        raise ValueError(f"no token action mapping for tool: {step.tool}")

    scope = {}

    if step.tool == "PATCH_APPLY":
        from sandbox.mounts import get_workspace_root

        requested_path = step.args["path"]
        workspace_root = get_workspace_root()
        resolved_path = (workspace_root / requested_path).resolve()

        try:
            resolved_path.relative_to(workspace_root.resolve())
        except ValueError as e:
            raise ValueError("patch path escapes workspace") from e

        scope = {"path": str(resolved_path)}

    token = issue_token(
        actions=[action],
        scope=scope,
        constraints={
            "plan_step_id": step.step_id,
            "plan_tool": step.tool,
        },
        ttl_seconds=300,
    )

    return token.id

def _result_exit_code(result: dict) -> int | None:
    if isinstance(result, dict):
        value = result.get("exit_code")
        if isinstance(value, int):
            return value
    return None


def _result_timed_out(result: dict) -> bool:
    return bool(isinstance(result, dict) and result.get("timed_out") is True)


def _changed_paths_from_results(results: list[dict]) -> list[str]:
    changed = []

    for item in results:
        if item["tool"] != "PATCH_APPLY":
            continue

        result = item.get("result")
        if isinstance(result, str) and result.startswith("[ERROR"):
            continue

        path = item.get("path")
        if isinstance(path, str) and path not in changed:
            changed.append(path)

    return changed

def _test_summary_from_results(results: List[Dict]) -> Dict:
    total = 0
    passed = 0
    failed = 0

    for item in results:
        if item["tool"] != "TEST_RUN":
            continue

        total += 1
        result = item["result"]

        if _result_timed_out(result):
            failed += 1
            continue

        exit_code = _result_exit_code(result)
        if exit_code == 0:
            passed += 1
        else:
            failed += 1

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
    }


def _classify_success_or_failure(results: list[dict], error: Exception | None) -> str:
    if error is not None:
        message = str(error).lower()
        if "not approved" in message:
            return "PLAN_INVALID"
        if "already executed" in message or "replay" in message:
            return "REPLAY_DENIED"
        if "step cap" in message:
            return "STEP_LIMIT_EXCEEDED"
        if "time budget" in message:
            return "TIME_BUDGET_EXCEEDED"
        if "capability" in message or "insufficient_scope" in message:
            return "CAPABILITY_DENIED"
        return "FAILED"

    for item in results:
        tool = item["tool"]
        result = item["result"]

        if tool == "TEST_RUN":
            if _result_timed_out(result):
                return "TIME_BUDGET_EXCEEDED"

            exit_code = _result_exit_code(result)
            if exit_code not in (None, 0):
                return "TEST_FAILURE"

        if tool == "PATCH_APPLY":
            if isinstance(result, str) and result.startswith("[ERROR"):
                return "PATCH_REJECTED"

        if tool == "GIT_RUN":
            if isinstance(result, dict):
                exit_code = _result_exit_code(result)
                if exit_code not in (None, 0):
                    return "FAILED"

    return "SUCCESS"

def _build_summary(
    *,
    plan_hash: str,
    tx_id: str,
    results: List[Dict],
    status: str,
    started_at: str,
    finished_at: str,
) -> Dict:

    summary = {
        "plan_hash": plan_hash,
        "tx_id": tx_id,
        "execution_status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "steps_attempted": len(results),
        "steps_completed": len(results),
        "test_summary": _test_summary_from_results(results),
        "changed_paths": _changed_paths_from_results(results),
        "requires_new_approval": status != "SUCCESS",
    }

    return summary


def _build_failure_envelope(
    *,
    plan_hash: str,
    tx_id: str,
    results: List[Dict],
    failure_class: str,
    error: Exception,
) -> Dict:

    failing_step_id = None
    failing_tool = None
    exit_code = None
    timed_out = False

    if results:
        last = results[-1]
        failing_step_id = last.get("step_id")
        failing_tool = last.get("tool")

        result = last.get("result", {})
        exit_code = _result_exit_code(result)
        timed_out = _result_timed_out(result)

    return {
        "plan_hash": plan_hash,
        "tx_id": tx_id,
        "result_status": "FAILED",
        "failure_class": failure_class,
        "failing_step_id": failing_step_id,
        "tool": failing_tool,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "changed_paths": _changed_paths_from_results(results),
        "error": str(error),
        "test_summary": _test_summary_from_results(results),
        "requires_new_approval": True,
    }


def _finalize_execution(
    *,
    plan_hash: str,
    tx_id: str,
    results: List[Dict],
    status: str,
    started_at: str,
    error: Exception | None = None,
):

    finished_at = _utc_now_iso()

    summary = _build_summary(
        plan_hash=plan_hash,
        tx_id=tx_id,
        results=results,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
    )

    write_summary(plan_hash, tx_id, summary)

    overwrite_executed_marker(
        plan_hash,
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "execution_started_at": started_at,
            "execution_finished_at": finished_at,
            "result_status": status,
        },
    )

    payload = {
        "plan_hash": plan_hash,
        "tx_id": tx_id,
        "results": results,
        "summary": summary,
    }

    log_event(
        "PLAN_SUMMARY_RECORDED",
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "execution_status": status,
        },
    )

    if status == "SUCCESS":

        log_event(
            "PLAN_EXECUTION_FINISHED",
            {
                "plan_hash": plan_hash,
                "tx_id": tx_id,
                "execution_status": status,
            },
        )

        return payload

    envelope = _build_failure_envelope(
        plan_hash=plan_hash,
        tx_id=tx_id,
        results=results,
        failure_class=status,
        error=error if error else RuntimeError(status),
    )

    write_failure_envelope(plan_hash, tx_id, envelope)

    log_event(
        "PLAN_FAILURE_ENVELOPE_RECORDED",
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "failure_class": status,
        },
    )

    log_event(
        "PLAN_EXECUTION_FAILED",
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "failure_class": status,
            "error": str(error) if error is not None else status,
        },
    )

    payload["failure_envelope"] = envelope
    return payload


# -----------------------------------------------------------------------------
# Execution
# -----------------------------------------------------------------------------

def execute_plan(gateway, plan_hash: str):

    if not plan_is_approved(plan_hash):

        log_event(
            "PLAN_EXECUTION_DENIED",
            {
                "plan_hash": plan_hash,
                "reason": "plan not approved",
            },
        )

        raise RuntimeError("plan not approved")

    if plan_has_executed(plan_hash):

        log_event(
            "PLAN_EXECUTION_REPLAY_DENIED",
            {
                "plan_hash": plan_hash,
                "reason": "plan already executed",
            },
        )

        raise RuntimeError("approved plan already executed")

    plan = load_approved_plan(plan_hash)

    if len(plan.steps) > MAX_STEPS_PER_EXECUTION:

        log_event(
            "PLAN_EXECUTION_DENIED",
            {
                "plan_hash": plan_hash,
                "reason": "step cap exceeded",
            },
        )

        raise RuntimeError("step cap exceeded")

    tx_id = _new_tx_id(plan_hash)
    started_at = _utc_now_iso()
    started_monotonic = time.monotonic()

    write_executed_marker(
        plan_hash,
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "execution_started_at": started_at,
            "result_status": "IN_PROGRESS",
        },
    )

    log_event(
        "PLAN_EXECUTION_STARTED",
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "steps": len(plan.steps),
        },
    )

    results: List[Dict] = []

    try:

        for step in plan.steps:

            elapsed = time.monotonic() - started_monotonic
            if elapsed > MAX_EXECUTION_SECONDS:
                raise RuntimeError("time budget exceeded")

            cap_token_id = _issue_step_token(step)

            step.args["cap_token_id"] = cap_token_id

            result = execute_step(gateway, step)

            record = {
                "step_id": step.step_id,
                "tool": step.tool,
                "result": result,
            }

            if step.tool == "PATCH_APPLY":
                record["path"] = step.args["path"]

            results.append(record)

            if _result_timed_out(result):
                raise RuntimeError("time budget exceeded")

            elapsed = time.monotonic() - started_monotonic
            if elapsed > MAX_EXECUTION_SECONDS:
                raise RuntimeError("time budget exceeded")

        status = _classify_success_or_failure(results, None)

        return _finalize_execution(
            plan_hash=plan_hash,
            tx_id=tx_id,
            results=results,
            status=status,
            started_at=started_at,
        )

    except Exception as e:

        failure_class = _classify_success_or_failure(results, e)

        return _finalize_execution(
            plan_hash=plan_hash,
            tx_id=tx_id,
            results=results,
            status=failure_class,
            started_at=started_at,
            error=e,
        )
