import pytest

from agent_core.plan_schema import Plan, ToolStep
from agent_core.plan_validator import validate_plan


def _plan_for(path):
    return Plan(
        plan_id="path-hygiene-test",
        steps=(
            ToolStep(
                step_id=1,
                tool="PATCH_APPLY",
                capability="patch.apply",
                args={"path": path, "new_content": "x\n"},
            ),
        ),
    )


@pytest.mark.parametrize("path", ["../escape.txt", "/tmp/escape.txt", "C:/tmp/escape.txt", "a//b.txt", "./x.txt"])
def test_validator_rejects_unsafe_mutation_paths(path):
    with pytest.raises(ValueError):
        validate_plan(_plan_for(path))


def test_validator_accepts_safe_relative_mutation_path():
    validate_plan(_plan_for("docs/safe.txt"))
