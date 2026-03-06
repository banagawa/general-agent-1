import json
from pathlib import Path
from dataclasses import asdict

from .plan_schema import Plan, ToolStep


PLAN_ROOT = Path("plans")
PENDING_DIR = PLAN_ROOT / "pending"
APPROVED_DIR = PLAN_ROOT / "approved"

PENDING_DIR.mkdir(parents=True, exist_ok=True)
APPROVED_DIR.mkdir(parents=True, exist_ok=True)


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


def _write_plan(path: Path, plan: Plan) -> None:
    path.write_text(
        json.dumps(_plan_to_dict(plan), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def pending_plan_path(plan_hash: str) -> Path:
    return PENDING_DIR / f"{plan_hash}.json"


def approved_plan_path(plan_hash: str) -> Path:
    return APPROVED_DIR / f"{plan_hash}.json"


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
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    src.unlink()
    return plan


def plan_is_approved(plan_hash: str) -> bool:
    return approved_plan_path(plan_hash).exists()
