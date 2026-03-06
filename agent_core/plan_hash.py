import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import Any

from .plan_schema import Plan


def _to_canonical_data(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)

    if isinstance(value, dict):
        return {str(k): _to_canonical_data(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}

    if isinstance(value, (list, tuple)):
        return [_to_canonical_data(v) for v in value]

    return value


def canonical_plan_json(plan: Plan) -> str:
    canonical_data = _to_canonical_data(plan)
    return json.dumps(
        canonical_data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def compute_plan_hash(plan: Plan) -> str:
    canonical_json = canonical_plan_json(plan)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
