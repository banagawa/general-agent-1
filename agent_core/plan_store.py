from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from sandbox.mounts import get_workspace_root

from .plan_schema import Plan, ToolStep


PLAN_ROOT = get_workspace_root() / "plans"
PENDING_DIR = PLAN_ROOT / "pending"
APPROVED_DIR = PLAN_ROOT / "approved"
EXECUTED_DIR = PLAN_ROOT / "executed"
FAILURES_DIR = PLAN_ROOT / "failures"
SUMMARIES_DIR = PLAN_ROOT / "summaries"

SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
PENDING_DIR.mkdir(parents=True, exist_ok=True)
APPROVED_DIR.mkdir(parents=True, exist_ok=True)
EXECUTED_DIR.mkdir(parents=True, exist_ok=True)
FAILURES_DIR.mkdir(parents=True, exist_ok=True)




def _plan_to_dict(plan: Plan) -> dict:
    return asdict(plan)


def _plan_from_dict(data: dict) -> Plan:
    steps = tuple(ToolStep(**step) for step in data["steps"])
    return Plan(
        plan_id=data["plan_id"],
        steps=steps,
    )


def _read_plan(path: Path) -> Plan:
    data = json.loads(path.read_text(encoding="utf-8"))
    return _plan_from_dict(data)


def _atomic_write_text(path: Path, content: str) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def _write_json(path: Path, payload: dict) -> None:
    content = json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )
    _atomic_write_text(path, content)


def _write_plan(path: Path, plan: Plan) -> None:
    _write_json(path, _plan_to_dict(plan))


def pending_plan_path(plan_hash: str) -> Path:
    return PENDING_DIR / f"{plan_hash}.json"


def approved_plan_path(plan_hash: str) -> Path:
    return APPROVED_DIR / f"{plan_hash}.json"


def executed_plan_path(plan_hash: str) -> Path:
    return EXECUTED_DIR / f"{plan_hash}.json"


def failure_envelope_path(plan_hash: str, tx_id: str) -> Path:
    return FAILURES_DIR / f"{plan_hash}-{tx_id}.json"


def store_pending_plan(plan_hash: str, plan: Plan) -> None:
    _write_plan(pending_plan_path(plan_hash), plan)


def load_pending_plan(plan_hash: str) -> Plan:
    path = pending_plan_path(plan_hash)
    if not path.exists():
        raise ValueError("pending plan not found")
    return _read_plan(path)


def load_approved_plan(plan_hash: str) -> Plan:
    path = approved_plan_path(plan_hash)
    if not path.exists():
        raise ValueError("approved plan not found")
    return _read_plan(path)


def mark_plan_approved(plan_hash: str) -> Plan:
    src = pending_plan_path(plan_hash)
    dst = approved_plan_path(plan_hash)

    if not src.exists():
        raise ValueError("pending plan not found")

    plan = _read_plan(src)
    _atomic_write_text(dst, src.read_text(encoding="utf-8"))
    src.unlink()
    return plan


def plan_is_approved(plan_hash: str) -> bool:
    return approved_plan_path(plan_hash).exists()


def plan_has_executed(plan_hash: str) -> bool:
    return executed_plan_path(plan_hash).exists()


def write_executed_marker(plan_hash: str, payload: dict) -> Path:
    path = executed_plan_path(plan_hash)
    if path.exists():
        raise RuntimeError("executed marker already exists")
    _write_json(path, payload)
    return path

def overwrite_executed_marker(plan_hash: str, payload: dict) -> Path:
    path = executed_plan_path(plan_hash)
    if not path.exists():
        raise RuntimeError("executed marker does not exist")
    _write_json(path, payload)
    return path

def write_failure_envelope(plan_hash: str, tx_id: str, payload: dict) -> Path:
    path = failure_envelope_path(plan_hash, tx_id)
    _write_json(path, payload)
    return path

def summary_path(plan_hash: str, tx_id: str) -> Path:
    return SUMMARIES_DIR / f"{plan_hash}-{tx_id}.json"


def write_summary(plan_hash: str, tx_id: str, payload: dict) -> Path:
    path = summary_path(plan_hash, tx_id)
    _write_json(path, payload)
    return path
