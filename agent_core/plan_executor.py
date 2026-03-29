from __future__ import annotations

import time
from datetime import datetime, UTC
from typing import Any, List, Dict
from audit.log import log_event
from policy.capabilities import issue_token

from agent_core.deny import deny_replay, deny_workspace_drift
from .execute_step import execute_step
from .plan_hash import compute_plan_hash
from .plan_validator import validate_plan
from agent_core.preflight import preflight_execute
from .plan_store import (
    load_approved_plan,
    load_approved_plan_meta,
    mark_plan_approved,
    overwrite_executed_marker,
    plan_has_executed,
    plan_is_approved,
    store_pending_plan,
    write_approved_plan_meta,
    write_executed_marker,
    write_failure_envelope,
    write_summary,
    transition_to_executed,
    transition_to_in_flight_atomic,
    transition_to_failed,
    STATE_EXECUTED,
    STATE_FAILED,
    STATE_IN_FLIGHT,
)
from .workspace_fingerprint import compute_workspace_fingerprint

TOKEN_ACTION_BY_TOOL = {
    "TEST_RUN": "CMD_RUN",
    "GIT_RUN": "GIT_RUN",
    "PATCH_APPLY": "FS_WRITE_PATCH",
    "FILE_CREATE": "FS_CREATE_FILE",
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

    plan = load_approved_plan(plan_hash)
    if plan is None:
        raise RuntimeError("approved plan not found")

    fingerprint = compute_workspace_fingerprint()

    write_approved_plan_meta(
        plan_hash,
        {
            "plan_hash": plan_hash,
            "plan_id": plan.plan_id,
            "approved_at": _utc_now_iso(),
            "approval_source": "manual",
            "workspace_fingerprint": fingerprint,
            "drift_check_enabled": True,
        },
    )

    log_event(
        "PLAN_APPROVED",
        {
            "plan_hash": plan_hash,
            "workspace_fingerprint": fingerprint,
            "drift_check_enabled": True,
        },
    )

    return {
        "plan_hash": plan_hash,
        "status": "APPROVED",
    }

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _intent_from_plan(plan) -> Dict:
    metadata = getattr(plan, "metadata", {})
    if not isinstance(metadata, dict):
        return {}

    intent = metadata.get("intent", {})
    if not isinstance(intent, dict):
        return {}

    goal = intent.get("goal")
    success_criteria = intent.get("success_criteria")

    return {
        "goal": goal if isinstance(goal, str) else None,
        "success_criteria": success_criteria if isinstance(success_criteria, list) else [],
    }

def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_tx_id(plan_hash: str) -> str:
    return f"{plan_hash[:12]}-{int(time.time())}"


def _issue_step_token(step):
    action = TOKEN_ACTION_BY_TOOL.get(step.tool)
    if not action:
        raise ValueError(f"no token action mapping for tool: {step.tool}")

    scope = {}

    if step.tool in {"PATCH_APPLY", "FILE_CREATE"}:
        from sandbox.mounts import get_workspace_root

        requested_path = step.args["path"]
        workspace_root = get_workspace_root()
        resolved_path = (workspace_root / requested_path).resolve()
        scope = {"path": str(resolved_path)}

        try:
            resolved_path.relative_to(workspace_root.resolve())
        except ValueError as e:
            raise ValueError("file path escapes workspace") from e

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
    '''
    NOTE:
    This function returns ONLY paths modified via PATCH_APPLY.
    It does NOT include FILE_CREATE paths.
    FILE_CREATE paths are handled separately via _created_paths_from_results.
    '''
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

        if "workspace drift" in message or "drift detected" in message:
            return "WORKSPACE_DRIFT_DENIED"

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
    plan,
    plan_hash: str,
    tx_id: str,
    results: List[Dict],
    status: str,
    started_at: str,
    finished_at: str,
) -> Dict:

    intent = _intent_from_plan(plan)
    created = _created_paths_from_results(results)
    modified = _changed_paths_from_results(results)
    summary = {
        "plan_hash": plan_hash,
        "tx_id": tx_id,
        "execution_status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "steps_attempted": len(results),
        "steps_completed": len(results),
        "test_summary": _test_summary_from_results(results),
        "created_paths": created,
        "modified_paths": modified,
        "changed_paths": created + [p for p in modified if p not in created],
        "requires_new_approval": status != "SUCCESS",
        "intent": intent,
    }

    return summary


def _build_failure_envelope(
    *,
    plan,
    plan_hash: str,
    tx_id: str,
    results: List[Dict],
    failure_class: str,
    error: Exception,
) -> Dict:

    intent = _intent_from_plan(plan)
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

    created = _created_paths_from_results(results)
    modified = _changed_paths_from_results(results)

    return {
        "plan_hash": plan_hash,
        "tx_id": tx_id,
        "result_status": "FAILED",
        "failure_class": failure_class,
        "failing_step_id": failing_step_id,
        "tool": failing_tool,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "created_paths": created,
        "modified_paths": modified,
        "changed_paths": created + [p for p in modified if p not in created],
        "error": str(error),
        "test_summary": _test_summary_from_results(results),
        "requires_new_approval": True,
        "intent": intent,
    }


def _finalize_execution(
    *,
    plan,
    plan_hash: str,
    tx_id: str,
    results: List[Dict],
    status: str,
    started_at: str,
    error: Exception | None = None,
):
    finished_at = _utc_now_iso()

    summary = _build_summary(
        plan = plan,
        plan_hash=plan_hash,
        tx_id=tx_id,
        results=results,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
    )

    write_summary(plan_hash, tx_id, summary)

    terminal_state = STATE_EXECUTED if status == "SUCCESS" else STATE_FAILED

    terminal_payload = {
        "plan_hash": plan_hash,
        "tx_id": tx_id,
        "state": terminal_state,
        "execution_started_at": started_at,
        "execution_finished_at": finished_at,
        "result_status": status,
    }

    if terminal_state == STATE_EXECUTED:
        transition_to_executed(plan_hash, terminal_payload)
    else:
        transition_to_failed(plan_hash, terminal_payload)

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
        plan=plan,
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

def _created_paths_from_results(results: list[dict]) -> list[str]:
    created = []

    for item in results:
        if item["tool"] != "FILE_CREATE":
            continue

        result = item.get("result")
        if isinstance(result, str) and result.startswith("[ERROR"):
            continue

        path = item.get("path")
        if isinstance(path, str) and path not in created:
            created.append(path)

    return created

# -----------------------------------------------------------------------------
# Execution
# -----------------------------------------------------------------------------

def execute_plan(gateway, plan_hash: str):

    preflight = preflight_execute(
        plan_hash,
        load_approved_plan=load_approved_plan,
        load_approval_meta=load_approved_plan_meta,
        recompute_plan_hash=compute_plan_hash,
        check_workspace_drift=_verify_workspace_drift,
    )

    plan = preflight.plan

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

    try:
        transition_to_in_flight_atomic(
            plan_hash,
            {
                "plan_hash": plan_hash,
                "tx_id": tx_id,
                "state": STATE_IN_FLIGHT,
                "execution_started_at": started_at,
            },
        )
    except FileExistsError:
        deny_replay(plan_hash)
        
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

            if step.tool in {"PATCH_APPLY", "FILE_CREATE"}:
                record["path"] = step.args["path"]

            results.append(record)

            if _result_timed_out(result):
                raise RuntimeError("time budget exceeded")

            elapsed = time.monotonic() - started_monotonic
            if elapsed > MAX_EXECUTION_SECONDS:
                raise RuntimeError("time budget exceeded")

        status = _classify_success_or_failure(results, None)

        return _finalize_execution(
            plan=plan,
            plan_hash=plan_hash,
            tx_id=tx_id,
            results=results,
            status=status,
            started_at=started_at,
        )

    except Exception as e:

        failure_class = _classify_success_or_failure(results, e)

        return _finalize_execution(
            plan=plan,
            plan_hash=plan_hash,
            tx_id=tx_id,
            results=results,
            status=failure_class,
            started_at=started_at,
            error=e,
        )
        
def _verify_workspace_drift(plan_hash: str) -> None:
    meta = load_approved_plan_meta(plan_hash)

    if not meta.get("drift_check_enabled", False):
        return

    approved_fingerprint = meta["workspace_fingerprint"]
    current_fingerprint = compute_workspace_fingerprint()

    if current_fingerprint == approved_fingerprint:
        return

    log_event(
        "PLAN_EXECUTION_DRIFT_DENIED",
        {
            "plan_hash": plan_hash,
            "approved_fingerprint": approved_fingerprint,
            "current_fingerprint": current_fingerprint,
        },
    )

    deny_workspace_drift(plan_hash, approved_fingerprint, current_fingerprint)


