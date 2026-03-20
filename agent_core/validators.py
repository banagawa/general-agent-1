from typing import Dict, Any
import re

PLAN_HASH_REGEX = re.compile(r"^[a-f0-9]{64}$")
PLAN_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


def validate_plan_hash(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("plan_hash must be a string")
    if not PLAN_HASH_REGEX.match(value):
        raise ValueError("invalid plan_hash format")
    return value


def validate_plan_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("plan_id must be a string")
    if not PLAN_ID_REGEX.match(value):
        raise ValueError("invalid plan_id format")
    return value


def validate_approved_meta(meta: Dict[str, Any]) -> None:
    if not isinstance(meta, dict):
        raise RuntimeError("approval metadata must be a dict")

    required_fields = {
        "plan_hash",
        "approved_at",
        "approval_source",
        "workspace_fingerprint",
        "plan_id",
    }

    # reject unknown fields
    unknown = set(meta.keys()) - required_fields - {"drift_check_enabled"}
    if unknown:
        raise RuntimeError(f"unknown approval metadata fields: {unknown}")

    for field in required_fields:
        if field not in meta:
            raise RuntimeError(f"missing required approval metadata field: {field}")

    if not isinstance(meta["plan_hash"], str):
        raise RuntimeError("plan_hash must be string")

    if not isinstance(meta["workspace_fingerprint"], str):
        raise RuntimeError("workspace_fingerprint must be string")

    if not isinstance(meta["approved_at"], str):
        raise RuntimeError("approved_at must be string")

    if not isinstance(meta["plan_id"], str):
        raise RuntimeError("plan_id must be string")

    if not isinstance(meta.get("drift_check_enabled", True), bool):
        raise RuntimeError("drift_check_enabled must be bool")

def validate_execution_request(plan_hash: str) -> str:
    if not isinstance(plan_hash, str):
        raise RuntimeError("invalid plan hash type")

    if not plan_hash:
        raise RuntimeError("plan hash empty")

    if len(plan_hash) != 64:
        raise RuntimeError("invalid plan hash length")

    if plan_hash.lower() != plan_hash:
        raise RuntimeError("plan hash must be lowercase")

    try:
        int(plan_hash, 16)
    except ValueError:
        raise RuntimeError("plan hash must be hex")

    return plan_hash
