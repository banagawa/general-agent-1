# Sprint A — CMD_RUN

Goal: Controlled command execution through ToolGateway.

---

## Requirements

- Strict allowlist
- No shell passthrough
- argv list only
- Forced cwd = WORKSPACE_ROOT
- Timeout enforced
- Output truncated
- Structured return
- Audit allow + deny

---

## Policy Layer

validate_cmd_run(argv)

- Must be list/tuple
- Non-empty
- Strings only
- No shell metacharacters
- Command must be in allowlist
- Subcommands validated (e.g., git status only)

---

## Runner

subprocess.run(
    shell=False,
    cwd=WORKSPACE_ROOT,
    timeout=DEFAULT_TIMEOUT,
    capture_output=True,
    text=True
)

Return:

{
  exit_code,
  stdout,
  stderr,
  stdout_truncated,
  stderr_truncated,
  duration_ms,
  timed_out
}

---

## Audit Events

CMD_RUN_DENIED  
CMD_RUN_EXECUTED  

Include:

- argv
- exit_code
- duration_ms
- timed_out
- truncation flags

---

## Allowed Commands (Initial)

python  
git (status, diff, log, show)

---

## Disallowed

bash  
sh  
cmd  
powershell  
curl  
wget  
pip (unless explicitly added later)
