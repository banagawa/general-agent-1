import json
import re
import subprocess
import sys
from pathlib import Path
import time

REPO_ROOT = Path(__file__).resolve().parent
MAIN = [sys.executable, "main.py"]
WORKSPACE = REPO_ROOT / "workspace"
PLANS = WORKSPACE / "plans"
AUDIT_FILE = REPO_ROOT / ".audit" / "audit.jsonl"
TMP_FILE = WORKSPACE / "drift_check_tmp.txt"


def run_cmd(arg: str, timeout: int = 30) -> tuple[int, str]:
    proc = subprocess.run(
        MAIN + [arg],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode, out


def expect(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def parse_plan_hash(output: str) -> str:
    m = re.search(r"PLAN_HASH=([0-9a-f]{64})", output)
    if not m:
        raise AssertionError(f"missing PLAN_HASH in output:\n{output}")
    return m.group(1)


def submit_test_run_plan(plan_id: str) -> str:

    unique_plan_id = f"{plan_id}-{int(time.time_ns())}"

    payload = {
        "plan_id": unique_plan_id,
        "steps": [
            {
                "step_id": 1,
                "tool": "TEST_RUN",
                "capability": "test.run",
                "args": {
                    "argv": ["python", "--version"],
                    "timeout_seconds": 10,
                },
            }
        ],
    }

    rc, out = run_cmd(f"plan.submit:{json.dumps(payload, separators=(',', ':'))}")
    expect(rc == 0, f"submit failed:\n{out}")
    expect("STATUS=PENDING_APPROVAL" in out, f"submit did not pend:\n{out}")
    return parse_plan_hash(out)

def approve_plan(plan_hash: str) -> None:
    rc, out = run_cmd(f"plan.approve:{plan_hash}")
    expect(rc == 0, f"approve failed:\n{out}")
    expect(f"PLAN_APPROVED {plan_hash}" in out, f"approve output unexpected:\n{out}")


def execute_plan(plan_hash: str) -> tuple[bool, str, dict | None]:
    rc, out = run_cmd(f"plan.execute:{plan_hash}", timeout=60)
    expect(rc == 0, f"execute nonzero exit:\n{out}")
    try:
        payload = json.loads(out)
        return True, out, payload
    except Exception:
        return False, out, None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_contains(event_name: str, plan_hash: str) -> bool:
    if not AUDIT_FILE.exists():
        return False
    for line in AUDIT_FILE.read_text(encoding="utf-8").splitlines():
        if event_name in line and plan_hash in line:
            return True
    return False


def approved_meta_path(plan_hash: str) -> Path:
    return PLANS / "approved" / f"{plan_hash}.meta.json"


def main() -> int:
    print("Workspace drift binding checks")
    print("=============================")

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    TMP_FILE.write_text("alpha\n", encoding="utf-8")

    # 1) approve writes metadata sidecar
    print("\n[1] approval metadata sidecar")
    hash1 = submit_test_run_plan("drift-meta-check")
    approve_plan(hash1)

    meta_path = approved_meta_path(hash1)
    expect(meta_path.exists(), f"missing approved metadata sidecar: {meta_path}")

    meta = load_json(meta_path)
    expect(meta.get("plan_hash") == hash1, f"bad meta plan_hash:\n{meta}")
    expect(bool(meta.get("workspace_fingerprint")), f"missing workspace_fingerprint:\n{meta}")
    expect(meta.get("drift_check_enabled") is True, f"drift_check_enabled not true:\n{meta}")
    print("PASS")

    # 2) clean approve -> execute still succeeds
    print("\n[2] clean approve -> execute succeeds")
    ok, out, payload = execute_plan(hash1)
    expect(ok and isinstance(payload, dict), f"expected JSON payload:\n{out}")
    expect(payload["summary"]["execution_status"] == "SUCCESS", f"expected SUCCESS:\n{json.dumps(payload, indent=2)}")
    print("PASS")

    # 3) approve, then drift, then deny execute
    print("\n[3] drift after approval causes denial/failure")
    hash2 = submit_test_run_plan("drift-deny-check")
    approve_plan(hash2)

    # create drift after approval
    with TMP_FILE.open("a", encoding="utf-8") as f:
        f.write("drift\n")

    ok, out, payload = execute_plan(hash2)
    if ok and isinstance(payload, dict):
        status = payload["summary"]["execution_status"]
        expect(status == "WORKSPACE_DRIFT_DENIED", f"expected WORKSPACE_DRIFT_DENIED:\n{json.dumps(payload, indent=2)}")
    else:
        lowered = out.lower()
        expect("workspace drift detected" in lowered or "drift" in lowered, f"expected drift denial text:\n{out}")
    print("PASS")

    # 4) drift audit event exists
    print("\n[4] drift audit event recorded")
    expect(
        audit_contains("PLAN_EXECUTION_DRIFT_DENIED", hash2),
        f"missing PLAN_EXECUTION_DRIFT_DENIED for {hash2} in {AUDIT_FILE}",
    )
    print("PASS")

    # 5) re-approve after drift allows execution
    print("\n[5] re-approve after drift allows execution")
    hash3 = submit_test_run_plan("drift-reapprove-check")
    approve_plan(hash3)

    ok, out, payload = execute_plan(hash3)
    expect(ok and isinstance(payload, dict), f"expected JSON payload:\n{out}")
    expect(payload["summary"]["execution_status"] == "SUCCESS", f"expected SUCCESS after re-approve:\n{json.dumps(payload, indent=2)}")
    print("PASS")

    print("\nAll workspace drift binding checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
