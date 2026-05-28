from __future__ import annotations

from agent_core.outcomes import CycleOutcome


def test_cycle_outcome_contains_existing_executor_statuses() -> None:
    expected = {
        "SUCCESS",
        "PLAN_INVALID",
        "REPLAY_DENIED",
        "WORKSPACE_DRIFT_DENIED",
        "STEP_LIMIT_EXCEEDED",
        "TIME_BUDGET_EXCEEDED",
        "CAPABILITY_DENIED",
        "FAILED",
        "TEST_FAILURE",
        "PATCH_REJECTED",
    }

    assert expected <= {outcome.value for outcome in CycleOutcome}


def test_cycle_outcome_contains_sprint_g_roadmap_statuses() -> None:
    expected = {
        "SUCCESS",
        "TEST_FAILURE",
        "BUILD_FAILURE",
        "PATCH_REJECTED",
        "PLAN_INVALID",
        "CAPABILITY_DENIED",
        "TIME_BUDGET_EXCEEDED",
        "STEP_LIMIT_EXCEEDED",
        "NO_EFFECT_DIFF",
    }

    assert expected <= {outcome.value for outcome in CycleOutcome}


def test_cycle_outcome_values_are_stable_strings() -> None:
    for outcome in CycleOutcome:
        assert outcome.value == outcome.name
