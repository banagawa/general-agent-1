from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Sequence, Dict, Any
from agent_core.security_invariants import assert_security_invariants

MAX_OUTPUT_BYTES = 64 * 1024  # 64KB
DEFAULT_TIMEOUT_SECONDS = 10


def _truncate(text: str, max_bytes: int) -> tuple[str, bool]:
    encoded = text.encode("utf-8", errors="ignore")
    if len(encoded) <= max_bytes:
        return text, False
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return truncated, True


def run_cmd(
    argv: Sequence[str],
    workspace_root: Path,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    Execute a validated command safely.
    Assumes policy validation already occurred.
    """

    if not isinstance(workspace_root, Path):
        workspace_root = Path(workspace_root)

    start = time.perf_counter()

    try:
        assert_security_invariants(shell=False, direct_tool_bypass=False)
        result = subprocess.run(
            list(argv),
            shell=False,                  # critical
            cwd=str(workspace_root),      # forced workspace
            timeout=timeout,
            capture_output=True,
            text=True,
        )

        duration_ms = int((time.perf_counter() - start) * 1000)

        stdout_trunc, stdout_was_truncated = _truncate(
            result.stdout or "", MAX_OUTPUT_BYTES
        )
        stderr_trunc, stderr_was_truncated = _truncate(
            result.stderr or "", MAX_OUTPUT_BYTES
        )

        return {
            "exit_code": result.returncode,
            "stdout": stdout_trunc,
            "stderr": stderr_trunc,
            "stdout_truncated": stdout_was_truncated,
            "stderr_truncated": stderr_was_truncated,
            "duration_ms": duration_ms,
            "timed_out": False,
        }

    except subprocess.TimeoutExpired as e:
        duration_ms = int((time.perf_counter() - start) * 1000)

        stdout_trunc, stdout_was_truncated = _truncate(
            e.stdout or "", MAX_OUTPUT_BYTES
        )
        stderr_trunc, stderr_was_truncated = _truncate(
            e.stderr or "", MAX_OUTPUT_BYTES
        )

        return {
            "exit_code": None,
            "stdout": stdout_trunc,
            "stderr": stderr_trunc,
            "stdout_truncated": stdout_was_truncated,
            "stderr_truncated": stderr_was_truncated,
            "duration_ms": duration_ms,
            "timed_out": True,
        }
