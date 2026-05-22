from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _safe_import(name: str) -> str | None:
    try:
        module = __import__(name, fromlist=["*"])
        return getattr(module, "__file__", None)
    except Exception as exc:
        return f"IMPORT_ERROR: {type(exc).__name__}: {exc}"


def main() -> int:
    print("=== runtime resolution probe ===")
    print(f"cwd={Path.cwd().resolve()}")
    print(f"repo_root={REPO_ROOT}")
    print(f"argv0={sys.argv[0]}")
    print(f"executable={sys.executable}")
    print(f"PYTHONPATH={os.environ.get('PYTHONPATH')!r}")

    print("\n=== sys.path ===")
    for index, value in enumerate(sys.path):
        print(f"{index}: {value}")

    print("\n=== module origins ===")
    for name in [
        "sandbox.mounts",
        "policy.engine",
        "agent_core.plan_executor",
        "agent_core.execute_step",
    ]:
        print(f"{name} -> {_safe_import(name)}")

    print("\n=== workspace resolution ===")
    try:
        import sandbox.mounts as mounts

        for attr in [
            "get_workspace_root",
            "get_app_root",
        ]:
            if hasattr(mounts, attr):
                try:
                    print(f"{attr}() -> {getattr(mounts, attr)()}")
                except Exception as exc:
                    print(f"{attr}() ERROR: {type(exc).__name__}: {exc}")
            else:
                print(f"{attr}() -> MISSING")
    except Exception as exc:
        print(f"sandbox.mounts import ERROR: {type(exc).__name__}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
