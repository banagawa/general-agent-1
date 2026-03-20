from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from audit.log import log_event


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deny(
    *,
    reason_code: str,
    reason: str,
    plan_hash: Optional[str] = None,
    plan_id: Optional[str] = None,
    prior_state: Optional[str] = None,
    new_state: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "timestamp": _now(),
        "reason_code": reason_code,
        "reason": reason,
    }

    if plan_hash:
        payload["plan_hash"] = plan_hash
    if plan_id:
        payload["plan_id"] = plan_id
    if prior_state:
        payload["prior_state"] = prior_state
    if new_state:
        payload["new_state"] = new_state
    if extra:
        payload.update(extra)

    log_event("DENY", payload)

    raise RuntimeError(reason)

def deny_replay(plan_hash: str) -> None:
    _deny(
        reason_code="PLAN_REPLAY_DENIED",
        reason="approved plan already executed",
        plan_hash=plan_hash,
    )


def deny_workspace_drift(plan_hash: str, approved: str, current: str) -> None:
    _deny(
        reason_code="PLAN_EXECUTION_DRIFT_DENIED",
        reason="workspace drift detected",
        plan_hash=plan_hash,
        extra={
            "approved_fingerprint": approved,
            "current_fingerprint": current,
        },
    )


def deny_hash_mismatch(plan_hash: str) -> None:
    _deny(
        reason_code="PLAN_HASH_MISMATCH",
        reason="plan hash mismatch",
        plan_hash=plan_hash,
    )


def deny_invalid_plan_hash(value: str) -> None:
    _deny(
        reason_code="INVALID_PLAN_HASH",
        reason="invalid plan_hash format",
        extra={"value": value},
    )
