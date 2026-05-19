from __future__ import annotations

import json

from agent_core.loop import AgentLoop
from main import parse_task_arg


class DummyGateway:
    pass


def test_main_parser_allows_task_autonomy() -> None:
    payload = {"task": "verify autonomy command", "mode": "MANUAL"}

    parsed = parse_task_arg(f"task.autonomy:{json.dumps(payload)}")

    assert parsed.startswith("task.autonomy:")


def test_main_parser_denies_empty_task_autonomy_payload() -> None:
    try:
        parse_task_arg("task.autonomy:")
    except ValueError as e:
        assert "requires payload" in str(e)
    else:
        raise AssertionError("empty task.autonomy payload was not denied")


def test_task_autonomy_manual_creates_pending_plan() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "verify autonomy command",
        "mode": "MANUAL",
        "budget": {
            "max_cycles": 1,
            "max_runtime_seconds": 120,
            "max_mutation_steps": 1,
        },
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert "MODE=MANUAL" in result
    assert "PLAN_HASH=" in result
    assert "STATUS=PENDING_APPROVAL" in result
    assert "STOP_REASON=AWAITING_APPROVAL" in result
    assert "CYCLES_USED=1" in result
    assert "BUDGET_REMAINING=" in result
    assert '"cycles": 0' in result


def test_task_autonomy_assisted_creates_pending_plan() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "verify assisted autonomy command",
        "mode": "ASSISTED",
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert "MODE=ASSISTED" in result
    assert "PLAN_HASH=" in result
    assert "STATUS=PENDING_APPROVAL" in result
    assert "STOP_REASON=AWAITING_APPROVAL" in result


def test_task_autonomy_missing_task_is_denied() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {"mode": "MANUAL"}

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert result.startswith("DENIED: invalid payload:")
    assert "task is required" in result


def test_task_autonomy_missing_mode_is_denied() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {"task": "verify missing mode denial"}

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert result.startswith("DENIED: invalid payload:")
    assert "mode is required" in result


def test_task_autonomy_malformed_json_is_denied() -> None:
    loop = AgentLoop(DummyGateway())

    result = loop.run("task.autonomy:{not-json")

    assert result.startswith("DENIED: invalid payload:")


def test_task_autonomy_bounded_autonomous_disabled_by_default() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "try bounded autonomous",
        "mode": "BOUNDED_AUTONOMOUS",
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert "MODE=BOUNDED_AUTONOMOUS" in result
    assert "STATUS=DENIED" in result
    assert "STOP_REASON=DISABLED" in result
    assert "PLAN_HASH=" not in result


def test_task_autonomy_bounded_autonomous_feature_flag_still_stops_for_approval(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENT_BOUNDED_AUTONOMY_ENABLED", "1")

    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "try bounded autonomous with flag",
        "mode": "BOUNDED_AUTONOMOUS",
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert "MODE=BOUNDED_AUTONOMOUS" in result
    assert "PLAN_HASH=" in result
    assert "STATUS=PENDING_APPROVAL" in result
    assert "STOP_REASON=AWAITING_APPROVAL" in result


def test_task_autonomy_non_integer_budget_is_denied() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "verify malformed budget denial",
        "mode": "MANUAL",
        "budget": {
            "max_cycles": "1",
        },
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert result.startswith("DENIED: invalid payload:")
    assert "max_cycles must be positive int" in result
    assert "PLAN_HASH=" not in result


def test_task_autonomy_zero_budget_is_denied() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "verify zero budget denial",
        "mode": "MANUAL",
        "budget": {
            "max_cycles": 0,
        },
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert result.startswith("DENIED: invalid payload:")
    assert "max_cycles must be positive int" in result
    assert "PLAN_HASH=" not in result


def test_task_autonomy_budget_must_be_object() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "verify budget object denial",
        "mode": "MANUAL",
        "budget": "not-object",
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert result.startswith("DENIED: invalid payload:")
    assert "budget must be object" in result
    assert "PLAN_HASH=" not in result


def test_task_autonomy_exhausted_runtime_budget_denies_before_plan() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "verify runtime budget exhaustion",
        "mode": "MANUAL",
        "budget": {
            "max_runtime_seconds": 120,
            "runtime_seconds_used": 120,
        },
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert "STATUS=DENIED" in result
    assert "STOP_REASON=BUDGET_EXHAUSTED" in result
    assert "PLAN_HASH=" not in result


def test_task_autonomy_exhausted_cycle_budget_denies_before_plan() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "verify cycle budget exhaustion",
        "mode": "MANUAL",
        "budget": {
            "max_cycles": 1,
            "cycles_used": 1,
        },
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert "STATUS=DENIED" in result
    assert "STOP_REASON=BUDGET_EXHAUSTED" in result
    assert "BUDGET_REMAINING=" in result
    assert "PLAN_HASH=" not in result


def test_task_autonomy_negative_budget_counter_is_denied() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "verify negative budget counter denial",
        "mode": "MANUAL",
        "budget": {
            "runtime_seconds_used": -1,
        },
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert result.startswith("DENIED: invalid payload:")
    assert "runtime_seconds_used must be nonnegative int" in result
    assert "PLAN_HASH=" not in result
