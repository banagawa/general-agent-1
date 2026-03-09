from __future__ import annotations

import json
import os
import time
import hashlib
from agent_core.plan_schema import Plan, ToolStep
from dataclasses import dataclass, asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import replace

from audit.log import log_event
from policy.capabilities import issue_token

from .execute_step import execute_step
from .plan_hash import compute_plan_hash
from .plan_store import (
    load_approved_plan,
    mark_plan_approved,
    plan_is_approved,
    store_pending_plan,
)
from .plan_validator import validate_plan

MAX_PLAN_STEPS = 20
MAX_TX_SECONDS = 120
MAX_MUTATIONS = 10
PLAN_STORE_ROOT = Path("plans")
APPROVED_PLANS_DIR = PLAN_STORE_ROOT / "approved"
EXECUTED_PLANS_DIR = PLAN_STORE_ROOT / "executed"
FAILURE_ENVELOPES_DIR = PLAN_STORE_ROOT / "failures"
SUMMARY_ARTIFACTS_DIR = PLAN_STORE_ROOT / "summaries"

TOKEN_ACTION_BY_TOOL = {
    "TEST_RUN": "CMD_RUN",
    "GIT_RUN": "GIT_RUN",
    "PATCH_APPLY": "FS_WRITE_PATCH",
}

PENDING_PLANS_DIR = Path("plans/pending")
APPROVED_PLANS_DIR = Path("plans/approved")


@dataclass(frozen=True)
class ExecutionContext:
    plan_hash: str
    tx_id: str
    started_at: str


def submit_plan(plan):
    validate_plan(plan)

    plan_payload = asdict(plan)
    plan_hash = compute_plan_hash(plan_payload)
    store_pending_plan(plan_hash, plan_payload)

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

def _issue_step_token(step):
    action = TOKEN_ACTION_BY_TOOL.get(step.tool)
    if not action:
        raise ValueError(f"no token action mapping for tool: {step.tool}")

    scope = {}
    if step.tool == "PATCH_APPLY":
        scope = {"path": step.args["path"]}

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


def _step_with_token(step, cap_token_id: str):
    args = dict(step.args)
    args["cap_token_id"] = cap_token_id
    return replace(step, args=args)

def execute_plan(gateway, plan_hash: str) -> Dict[str, Any]:
    if not plan_is_approved(plan_hash):
        _audit_execution_denied(plan_hash, "plan not approved")
        raise RuntimeError("plan not approved")

    if execution_marker_exists(plan_hash):
        _audit_replay_denied(plan_hash)
        raise RuntimeError("plan already executed")

    plan = load_approved_plan(plan_hash)
    _enforce_step_cap(plan)

    drift_status = verify_workspace_fingerprint_if_enabled(plan_hash, plan)

    ctx = ExecutionContext(
        plan_hash=plan_hash,
        tx_id=_new_tx_id(plan_hash),
        started_at=_utc_now(),
    )

    _audit_execution_started(plan_hash, len(plan.steps), ctx.tx_id)

    step_results: List[Dict[str, Any]] = []
    changed_paths: List[str] = []
    mutation_count = 0

    try:
        for step in plan.steps:
            _enforce_time_budget(ctx)

            cap_token_id = _issue_step_token(step)
            step_with_token = _step_with_token(step, cap_token_id)

            result = execute_step(gateway, step_with_token)

            if step.tool == "PATCH_APPLY":
                mutation_count += 1
                if mutation_count > MAX_MUTATIONS:
                    raise RuntimeError("mutation cap exceeded")

            step_results.append(
                {
                    "step_id": step.step_id,
                    "tool": step.tool,
                    "result": result,
                }
            )

            changed_paths.extend(_extract_changed_paths(step, result))

        test_summary = _collect_test_summary(step_results)
        diff_summary = _collect_repo_diff(gateway)
        result_status = _derive_result_status(step_results)

        if result_status != "SUCCESS":
            failure_class = "test_failure" if not test_summary.get("passed", True) else "tool_error"

            failure_envelope = {
                "plan_hash": plan_hash,
                "tx_id": ctx.tx_id,
                "result_status": "FAILED",
                "failing_step_id": _last_step_id(step_results),
                "tool": _last_tool(step_results),
                "failure_class": failure_class,
                "error": "execution completed with failed step result",
                "changed_paths": sorted(set(changed_paths)),
                "test_summary": test_summary,
                "diff_summary": diff_summary,
                "requires_new_approval": True,
            }

            _record_failure_envelope(failure_envelope)

            summary = _build_execution_summary(
                plan_hash=plan_hash,
                tx_id=ctx.tx_id,
                result_status="FAILED",
                step_results=step_results,
                test_summary=test_summary,
                diff_summary=diff_summary,
                replay_status="not_replayed",
                drift_status=drift_status,
                requires_new_approval=True,
                mutation_count=mutation_count,
            )

            _record_summary(summary)
            _audit_execution_failed(plan_hash, ctx.tx_id, failure_class)

            return {
                "plan_hash": plan_hash,
                "tx_id": ctx.tx_id,
                "summary": summary,
                "failure_envelope": failure_envelope,
                "results": step_results,
            }

        summary = _build_execution_summary(
            plan_hash=plan_hash,
            tx_id=ctx.tx_id,
            result_status="SUCCESS",
            step_results=step_results,
            test_summary=test_summary,
            diff_summary=diff_summary,
            replay_status="not_replayed",
            drift_status=drift_status,
            requires_new_approval=False,
            mutation_count=mutation_count,
        )

        _record_summary(summary)
        _write_executed_marker_atomic(
            plan_hash=plan_hash,
            tx_id=ctx.tx_id,
            result_status="SUCCESS",
        )
        _audit_execution_finished(plan_hash, len(step_results), ctx.tx_id)

        return {
            "plan_hash": plan_hash,
            "tx_id": ctx.tx_id,
            "summary": summary,
            "results": step_results,
        }

    except Exception as exc:
        failure_class = classify_execution_failure(exc)

        test_summary = _collect_test_summary(step_results)
        diff_summary = _collect_repo_diff(gateway)

        failure_envelope = {
            "plan_hash": plan_hash,
            "tx_id": ctx.tx_id,
            "result_status": "FAILED",
            "failing_step_id": _last_step_id(step_results),
            "tool": _last_tool(step_results),
            "failure_class": failure_class,
            "error": str(exc),
            "changed_paths": sorted(set(changed_paths)),
            "test_summary": test_summary,
            "diff_summary": diff_summary,
            "requires_new_approval": True,
        }

        _record_failure_envelope(failure_envelope)

        summary = _build_execution_summary(
            plan_hash=plan_hash,
            tx_id=ctx.tx_id,
            result_status="FAILED",
            step_results=step_results,
            test_summary=test_summary,
            diff_summary=diff_summary,
            replay_status="not_replayed",
            drift_status=drift_status,
            requires_new_approval=True,
            mutation_count=mutation_count,
        )

        _record_summary(summary)
        _audit_execution_failed(plan_hash, ctx.tx_id, failure_class)

        return {
            "plan_hash": plan_hash,
            "tx_id": ctx.tx_id,
            "summary": summary,
            "failure_envelope": failure_envelope,
            "results": step_results,
        }

def verify_workspace_fingerprint_if_enabled(plan_hash: str, plan) -> str:
    return "not_enforced"

def _enforce_step_cap(plan) -> None:
    if len(plan.steps) > MAX_PLAN_STEPS:
        raise RuntimeError("step cap exceeded")


def _enforce_time_budget(ctx: ExecutionContext) -> None:
    started = _parse_utc_timestamp(ctx.started_at)
    elapsed = time.time() - started
    if elapsed > MAX_TX_SECONDS:
        raise RuntimeError("transaction timeout")


def _collect_test_summary(step_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    tests = [r for r in step_results if r["tool"] == "TEST_RUN"]
    passed = all(_result_ok(t["result"]) for t in tests) if tests else True
    return {
        "count": len(tests),
        "passed": passed,
    }


def _collect_repo_diff(gateway) -> Dict[str, Any]:
    diff_res = gateway.git_run(
        argv=["git", "diff", "--stat"],
        timeout_seconds=10,
        cap_token_id=None,
    )

    status_res = gateway.git_run(
        argv=["git", "status", "--short"],
        timeout_seconds=10,
        cap_token_id=None,
    )

    return {
        "diff_stat": {
            "ok": bool(diff_res.get("ok")),
            "exit_code": diff_res.get("exit_code"),
            "stdout": diff_res.get("stdout", ""),
            "stderr": diff_res.get("stderr", ""),
            "timed_out": bool(diff_res.get("timed_out", False)),
            "denied": bool(diff_res.get("denied", False)),
            "reason": diff_res.get("reason"),
        },
        "status_short": {
            "ok": bool(status_res.get("ok")),
            "exit_code": status_res.get("exit_code"),
            "stdout": status_res.get("stdout", ""),
            "stderr": status_res.get("stderr", ""),
            "timed_out": bool(status_res.get("timed_out", False)),
            "denied": bool(status_res.get("denied", False)),
            "reason": status_res.get("reason"),
        },
    }

def _build_execution_summary(
    *,
    plan_hash: str,
    tx_id: str,
    result_status: str,
    step_results: List[Dict[str, Any]],
    test_summary: Dict[str, Any],
    diff_summary: Dict[str, Any],
    replay_status: str,
    drift_status: str,
    requires_new_approval: bool,
    mutation_count: int,
) -> Dict[str, Any]:
    return {
        "plan_hash": plan_hash,
        "tx_id": tx_id,
        "result_status": result_status,
        "steps_attempted": len(step_results),
        "steps_completed": len(step_results),
        "mutation_count": mutation_count,
        "test_summary": test_summary,
        "diff_summary": diff_summary,
        "replay_status": replay_status,
        "drift_status": drift_status,
        "requires_new_approval": requires_new_approval,
    }


def execution_marker_exists(plan_hash: str) -> bool:
    return _executed_marker_path(plan_hash).exists()


def _write_executed_marker_atomic(
    *,
    plan_hash: str,
    tx_id: str,
    result_status: str,
) -> Path:
    marker_path = _executed_marker_path(plan_hash)
    _ensure_parent_dir(marker_path)

    if marker_path.exists():
        raise RuntimeError("plan already executed")

    payload = {
        "plan_hash": plan_hash,
        "executed_at": _utc_now(),
        "execution_count": 1,
        "result_status": result_status,
        "tx_id": tx_id,
    }

    _atomic_write_json(marker_path, payload, overwrite=False)
    return marker_path


def _record_failure_envelope(failure_envelope: Dict[str, Any]) -> Path:
    plan_hash = str(failure_envelope["plan_hash"])
    tx_id = str(failure_envelope["tx_id"])
    envelope_path = _failure_envelope_path(plan_hash, tx_id)

    _atomic_write_json(envelope_path, failure_envelope, overwrite=False)
    _audit_failure_envelope_recorded(plan_hash, tx_id, envelope_path)
    return envelope_path


def _record_summary(summary: Dict[str, Any]) -> Path:
    plan_hash = str(summary["plan_hash"])
    tx_id = str(summary["tx_id"])
    summary_path = _summary_artifact_path(plan_hash, tx_id)

    _atomic_write_json(summary_path, summary, overwrite=False)
    _audit_summary_recorded(plan_hash, tx_id, summary_path)
    return summary_path


def _executed_marker_path(plan_hash: str) -> Path:
    return EXECUTED_PLANS_DIR / f"{plan_hash}.json"


def _failure_envelope_path(plan_hash: str, tx_id: str) -> Path:
    return FAILURE_ENVELOPES_DIR / f"{plan_hash}-{tx_id}.json"


def _summary_artifact_path(plan_hash: str, tx_id: str) -> Path:
    return SUMMARY_ARTIFACTS_DIR / f"{plan_hash}-{tx_id}.json"


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, payload: Dict[str, Any], *, overwrite: bool) -> None:
    _ensure_parent_dir(path)

    if path.exists() and not overwrite:
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")

    temp_path = path.with_name(f".{path.name}.tmp-{os.getpid()}-{int(time.time() * 1000)}")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    try:
        if not overwrite and path.exists():
            temp_path.unlink(missing_ok=True)
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def classify_execution_failure(exc: Exception) -> str:
    text = str(exc).lower()

    if "summary" in text and ("fail" in text or "error" in text):
        return "execution_summary_generation_failure"
    if "workspace drift" in text or "drift denied" in text:
        return "workspace_drift_denial"
    if "already executed" in text or "replay" in text:
        return "replay_denial"
    if "capability" in text:
        return "capability_denial"
    if "policy" in text:
        return "policy_denial"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "validation" in text or "malformed" in text or "not approved" in text:
        return "validation_error"
    if "test" in text or "pytest" in text:
        return "test_failure"
    return "tool_error"

def _parse_utc_timestamp(timestamp: str) -> float:
    normalized = timestamp.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).timestamp()


def _last_step_id(step_results: List[Dict[str, Any]]) -> Optional[Any]:
    if not step_results:
        return None
    return step_results[-1].get("step_id")


def _last_tool(step_results: List[Dict[str, Any]]) -> Optional[str]:
    if not step_results:
        return None
    return step_results[-1].get("tool")

    if "ok" in result:
        return bool(result["ok"])
    if "success" in result:
        return bool(result["success"])
    if "exit_code" in result:
        return int(result["exit_code"]) == 0
    return bool(result)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_tx_id(plan_hash: str) -> str:
    return f"tx-{plan_hash[:12]}-{int(datetime.now(timezone.utc).timestamp())}"


def _audit_failure_envelope_recorded(plan_hash: str, tx_id: str, path: Path) -> None:
    log_event(
        "PLAN_FAILURE_ENVELOPE_RECORDED",
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "path": str(path),
        },
    )


def _audit_summary_recorded(plan_hash: str, tx_id: str, path: Path) -> None:
    log_event(
        "PLAN_SUMMARY_RECORDED",
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "path": str(path),
        },
    )
# ---------------------------------------------------------------------
# Sprint D/E plan store + audit helpers
# ---------------------------------------------------------------------


def plan_is_approved(plan_hash: str) -> bool:
    return (APPROVED_PLANS_DIR / f"{plan_hash}.json").exists()


def load_approved_plan(plan_hash: str):
    path = APPROVED_PLANS_DIR / f"{plan_hash}.json"
    if not path.exists():
        raise RuntimeError("plan not approved")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    raw_steps = data.get("steps", [])
    steps = tuple(
        ToolStep(
            step_id=step["step_id"],
            tool=step["tool"],
            capability=step["capability"],
            args=step["args"],

        )
        for step in raw_steps
    )

    return Plan(
        plan_id=data["plan_id"],
        steps=steps,
    )

def store_pending_plan(plan_hash: str, plan_json: dict) -> None:
    PENDING_PLANS_DIR.mkdir(parents=True, exist_ok=True)

    path = PENDING_PLANS_DIR / f"{plan_hash}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(plan_json, f, indent=2)


def mark_plan_approved(plan_hash: str) -> None:
    pending = PENDING_PLANS_DIR / f"{plan_hash}.json"
    approved = APPROVED_PLANS_DIR / f"{plan_hash}.json"

    if not pending.exists():
        raise RuntimeError("pending plan not found")

    APPROVED_PLANS_DIR.mkdir(parents=True, exist_ok=True)
    pending.replace(approved)


def compute_plan_hash(plan_json: dict) -> str:
    raw = json.dumps(plan_json, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _result_ok(result: Any) -> bool:
    if isinstance(result, dict):
        if result.get("denied"):
            return False
        if result.get("timed_out"):
            return False
        if "exit_code" in result:
            return int(result["exit_code"]) == 0
        if "ok" in result:
            return bool(result["ok"])
    return bool(result)
    
# ---------------------------------------------------------------------
# execution audit helpers
# ---------------------------------------------------------------------

def _audit_execution_denied(plan_hash: str, reason: str) -> None:
    log_event(
        "PLAN_EXECUTION_DENIED",
        {"plan_hash": plan_hash, "reason": reason},
    )


def _audit_replay_denied(plan_hash: str) -> None:
    log_event(
        "PLAN_EXECUTION_REPLAY_DENIED",
        {"plan_hash": plan_hash},
    )


def _audit_execution_started(plan_hash: str, step_count: int, tx_id: str) -> None:
    log_event(
        "PLAN_EXECUTION_STARTED",
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "step_count": step_count,
        },
    )


def _audit_execution_finished(plan_hash: str, step_count: int, tx_id: str) -> None:
    log_event(
        "PLAN_EXECUTION_FINISHED",
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "step_count": step_count,
        },
    )


def _audit_execution_failed(plan_hash: str, tx_id: str, failure_class: str) -> None:
    log_event(
        "PLAN_EXECUTION_FAILED",
        {
            "plan_hash": plan_hash,
            "tx_id": tx_id,
            "failure_class": failure_class,
        },
    )


# ---------------------------------------------------------------------
# execution helpers
# ---------------------------------------------------------------------

def _extract_changed_paths(step, result) -> List[str]:
    if step.tool == "PATCH_APPLY":
        return [step.args["path"]]
    return []


def _derive_result_status(step_results: List[Dict[str, Any]]) -> str:
    for item in step_results:
        result = item.get("result")
        if not _result_ok(result):
            return "FAILED"
    return "SUCCESS"
