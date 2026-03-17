import re
import sys

from agent_core.orchestrator import Orchestrator


ALLOWED_COMMANDS = {
    "plan.submit",
    "plan.approve",
    "plan.execute",
    "task.plan",
}

PLAN_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_task_arg(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError("task must be a string")

    raw = raw.strip()
    if not raw:
        raise ValueError("empty task")

    if ":" not in raw:
        raise ValueError("command must be in form <command>:<payload>")

    command, payload = raw.split(":", 1)

    if command not in ALLOWED_COMMANDS:
        raise ValueError("unknown command")

    if command in {"plan.approve", "plan.execute"}:
        if not payload:
            raise ValueError(f"{command} requires plan hash payload")
        if any(ch.isspace() for ch in payload):
            raise ValueError(f"{command} payload must not contain whitespace")
        if not PLAN_HASH_RE.fullmatch(payload):
            raise ValueError(
                f"{command} payload must be a lowercase 64-character hex hash"
            )

    if command in {"plan.submit", "task.plan"}:
        if not payload.strip():
            raise ValueError(f"{command} requires payload")

    return raw


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py '<command>:<payload>'")
        return

    try:
        task = parse_task_arg(sys.argv[1])
    except ValueError as e:
        print(f"DENIED: {e}")
        return

    orchestrator = Orchestrator()
    result = orchestrator.handle(task)
    print(result)


if __name__ == "__main__":
    main()
