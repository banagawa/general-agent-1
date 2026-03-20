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
        raise ValueError("approval metadata must be a dict")

    required_fields = [
        "plan_hash",
        "approved_at",
        "approval_source",
        "workspace_fingerprint",
        "plan_id",
    ]

    for field in required_fields:
        if field not in meta:
            raise ValueError(f"missing required approval metadata field: {field}")

    validate_plan_hash(meta["plan_hash"])
    validate_plan_id(meta["plan_id"])

    if not isinstance(meta["approved_at"], str):
        raise ValueError("approved_at must be a string timestamp")

    if not isinstance(meta["approval_source"], str):
        raise ValueError("approval_source must be a string")

    if not isinstance(meta["workspace_fingerprint"], str):
        raise ValueError("workspace_fingerprint must be a string")

    # optional flags
    if "drift_check_enabled" in meta and not isinstance(meta["drift_check_enabled"], bool):
        raise ValueError("drift_check_enabled must be a boolean if present")
