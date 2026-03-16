#!/usr/bin/env python3
"""
Sprint E execution checks.

Runs a small end-to-end verification against main.py:
- submit -> approve -> execute success
- replay denial
- failing TEST_RUN -> summary + failure_envelope
- timeout -> TIME_BUDGET_EXCEEDED
- PATCH_APPLY positive path
- raw execution denied
- malformed approve hash denied

Assumptions:
- run from repo root
- main.py is in repo root
- Python is available via sys.executable
- workspace root is ./workspace for the patch/temp files this script creates
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent
MAIN = [sys.executable, "main.py"]
WORKSPACE_DIR = REPO_ROOT / "workspace"
TMP_FILE = WORKSPACE_DIR / "sprint_e_tmp.txt"


def run_cmd(arg: str, timeout: int = 30) -> tuple[int, str]:
    proc = subprocess.run(
        MAIN + [arg],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = (proc.stdout + proc.stderr).strip()
    return proc.returncode, output


def parse_plan_hash(output: str) -> str:
    match = re.search(r"PLAN_HASH=([0-9a-f]{64})", output)
    if not match:
        raise AssertionError(f"could not find PLAN_HASH in output:\n{output}")
    return match.group(1)


def parse_json_output(output: str) -> dict[str, Any]:
    try:
        return json.loads(output)
    except Exception as e:
        raise AssertionError(f"expected JSON output, got:\n{output}") from e


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_in(needle: str, haystack: str, label: str) -> None:
    expect(needle in haystack, f"missing {label!r} in output:\n{haystack}")


def print_case(name: str) -> None:
    print(f"\n=== {name} ===")


def submit_plan(plan: dict[str, Any]) -> str:
    payload = json.dumps(plan, separators=(",", ":"))
    rc, out = run_cmd(f"plan.submit:{payload}")
    expect(rc == 0, f"submit nonzero exit:\n{out}")
    expect_in("PLAN_HASH=", out, "PLAN_HASH")
    expect_in("STATUS=PENDING_APPROVAL", out, "pending status")
    return parse_plan_hash(out)


def approve_plan(plan_hash: str) -> None:
    rc, out = run_cmd(f"plan.approve:{plan_hash}")
    expect(rc == 0, f"approve nonzero exit:\n{out}")
    expect_in(f"PLAN_APPROVED {plan_hash}", out, "approval output")


def execute_plan(plan_hash: str, timeout: int = 300) -> dict[str, Any] | str:
    rc, out = run_cmd(f"plan.execute:{plan_hash}", timeout=timeout)
    expect(rc == 0, f"execute nonzero exit:\n{out}")
    try:
        return parse_json_output(out)
    except AssertionError:
        return out


def test_success_flow() -> None:
    print_case("success flow + replay deny")

    plan = {
        "plan_id": "exec-smoke-pass",
        "steps": [
            {
                "step_id": 1,
                "tool": "TEST_RUN",
                "capability": "test.run",
                "args": {"argv": ["python", "--version"], "timeout_seconds": 10},
            }
        ],
    }

    plan_hash = submit_plan(plan)

    rc, out = run_cmd(f"plan.execute:{plan_hash}")
    expect(rc == 0, f"pre-approval execute nonzero exit:\n{out}")
    expect("DENIED" in out or "not approved" in out.lower(), f"expected pre-approval deny:\n{out}")

    approve_plan(plan_hash)

    payload = execute_plan(plan_hash)
    expect(isinstance(payload, dict), f"expected JSON payload, got:\n{payload}")
    summary = payload["summary"]
    expect(summary["execution_status"] == "SUCCESS", f"unexpected status:\n{json.dumps(payload, indent=2)}")
    expect(summary["requires_new_approval"] is False, "success should not require new approval")
    expect(summary["test_summary"]["total"] == 1, "expected one test")
    expect(summary["test_summary"]["passed"] == 1, "expected one passed test")
    expect("failure_envelope" not in payload, "success payload should not include failure_envelope")

    replay = execute_plan(plan_hash)
    expect(isinstance(replay, str), "expected replay deny text output")
    expect("DENIED" in replay or "already executed" in replay.lower(), f"expected replay deny:\n{replay}")


def test_failure_flow() -> None:
    print_case("failing TEST_RUN -> failure envelope")

    plan = {
        "plan_id": "exec-smoke-fail",
        "steps": [
            {
                "step_id": 1,
                "tool": "TEST_RUN",
                "capability": "test.run",
                "args": {"argv": ["python", "-c", "import sys; sys.exit(7)"], "timeout_seconds": 10},
            }
        ],
    }

    plan_hash = submit_plan(plan)
    approve_plan(plan_hash)

    payload = execute_plan(plan_hash)
    expect(isinstance(payload, dict), f"expected JSON payload, got:\n{payload}")

    summary = payload["summary"]
    envelope = payload.get("failure_envelope")

    expect(summary["execution_status"] == "TEST_FAILURE", f"unexpected summary:\n{json.dumps(payload, indent=2)}")
    expect(summary["requires_new_approval"] is True, "failure should require new approval")
    expect(isinstance(envelope, dict), "missing failure_envelope")
    expect(envelope["failure_class"] == "TEST_FAILURE", f"unexpected envelope:\n{json.dumps(payload, indent=2)}")
    expect(envelope["tool"] == "TEST_RUN", f"unexpected tool in envelope:\n{json.dumps(payload, indent=2)}")


def test_timeout_flow() -> None:
    print_case("timeout -> TIME_BUDGET_EXCEEDED")

    plan = {
        "plan_id": "exec-smoke-timeout",
        "steps": [
            {
                "step_id": 1,
                "tool": "TEST_RUN",
                "capability": "test.run",
                "args": {"argv": ["python", "-c", "import time; time.sleep(200)"], "timeout_seconds": 200},
            }
        ],
    }

    plan_hash = submit_plan(plan)
    approve_plan(plan_hash)

    payload = execute_plan(plan_hash, timeout=260)
    expect(isinstance(payload, dict), f"expected JSON payload, got:\n{payload}")

    summary = payload["summary"]
    envelope = payload.get("failure_envelope")

    expect(summary["execution_status"] == "TIME_BUDGET_EXCEEDED", f"unexpected summary:\n{json.dumps(payload, indent=2)}")
    expect(isinstance(envelope, dict), "missing failure_envelope")
    expect(envelope["failure_class"] == "TIME_BUDGET_EXCEEDED", f"unexpected envelope:\n{json.dumps(payload, indent=2)}")
    expect(envelope["timed_out"] is True, f"expected timed_out true:\n{json.dumps(payload, indent=2)}")


def test_patch_apply_flow() -> None:
    print_case("PATCH_APPLY positive path")

    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    TMP_FILE.write_text("alpha\n", encoding="utf-8")

    plan = {
        "plan_id": "exec-smoke-patch",
        "steps": [
            {
                "step_id": 1,
                "tool": "PATCH_APPLY",
                "capability": "patch.apply",
                "args": {"path": "sprint_e_tmp.txt", "new_content": "beta\n"},
            }
        ],
    }

    plan_hash = submit_plan(plan)
    approve_plan(plan_hash)

    payload = execute_plan(plan_hash)
    expect(isinstance(payload, dict), f"expected JSON payload, got:\n{payload}")

    summary = payload["summary"]
    expect(summary["execution_status"] == "SUCCESS", f"unexpected patch summary:\n{json.dumps(payload, indent=2)}")
    expect("sprint_e_tmp.txt" in summary["changed_paths"], f"missing changed path:\n{json.dumps(payload, indent=2)}")
    expect(TMP_FILE.read_text(encoding="utf-8") == "beta\n", f"unexpected temp file contents:\n{TMP_FILE.read_text(encoding='utf-8')!r}")


def test_raw_execution_denied() -> None:
    print_case("raw execution denied")

    for raw in [
        "cmd.run: echo hello",
        "update file: foo.txt: hi",
        "propose patch: foo.txt: hi",
    ]:
        rc, out = run_cmd(raw)
        expect(rc == 0, f"nonzero exit for raw command:\n{out}")
        expect("DENIED" in out, f"expected DENIED for raw command {raw!r}:\n{out}")


def test_parser_hardening() -> None:
    print_case("parser hardening")

    valid_hash = "5083db379b25a1c70586bd2e5cf1d2f19f9717880ac53b0c9ea238c840f27e4b"

    for bad in [
        "plan.approve:abc",
        "plan.approve:abc def",
        "plan.delete:abc",
        "plan.approve",
        f"plan.approve:{valid_hash}:extra",
    ]:
        rc, out = run_cmd(bad)
        expect(rc == 0, f"nonzero exit for parser case:\n{out}")
        expect("DENIED" in out, f"expected parser denial for {bad!r}:\n{out}")


def test_plan_artifacts_exist() -> None:
    print_case("artifact spot check")

    ws_plans = WORKSPACE_DIR / "plans"
    executed_dir = ws_plans / "executed"
    failures_dir = ws_plans / "failures"
    summaries_dir = ws_plans / "summaries"

    expect(executed_dir.exists(), f"missing directory: {executed_dir}")
    expect(failures_dir.exists(), f"missing directory: {failures_dir}")
    expect(summaries_dir.exists(), f"missing directory: {summaries_dir}")

    executed = [p for p in executed_dir.glob("*") if p.is_file() and p.name != ".gitkeep"]
    failures = [p for p in failures_dir.glob("*") if p.is_file() and p.name != ".gitkeep"]
    summaries = [p for p in summaries_dir.glob("*") if p.is_file() and p.name != ".gitkeep"]

    expect(executed, "expected at least one executed marker in workspace/plans/executed")
    expect(failures, "expected at least one failure artifact in workspace/plans/failures")
    expect(summaries, "expected at least one summary artifact in workspace/plans/summaries")


def main() -> int:
    print("Sprint E execution checks")
    print("=========================")
    print(f"Repo root: {REPO_ROOT}")
    print(f"Python: {sys.executable}")

    checks = [
        test_success_flow,
        test_failure_flow,
        test_timeout_flow,
        test_patch_apply_flow,
        test_raw_execution_denied,
        test_parser_hardening,
        test_plan_artifacts_exist,
    ]

    failures: list[tuple[str, str]] = []
    started = time.time()

    for check in checks:
        try:
            check()
            print("PASS")
        except Exception as e:
            print("FAIL")
            failures.append((check.__name__, str(e)))

    elapsed = time.time() - started

    print("\n=========================")
    print(f"Elapsed: {elapsed:.1f}s")

    if failures:
        print("Failures:")
        for name, msg in failures:
            print(f"- {name}: {msg}")
        return 1

    print("All execution checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
