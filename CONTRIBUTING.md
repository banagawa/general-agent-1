
# Contributing Guidelines

This repository enforces strict architectural discipline.

Before contributing, read:

- docs/anchors/architecture-contract.md
- docs/anchors/system-state-v1.md
- SECURITY.md

---

## Non-Negotiable Rules

### 1. No Tool Bypass

All tool calls must go through ToolGateway.

Never call:
- subprocess directly from AgentLoop
- file system tools directly from loop
- policy checks outside gateway

---

### 2. No shell=True

subprocess must always use:

shell=False

Single-string command execution is forbidden.

---

### 3. Patch-Only Writes

- No direct file overwrite.
- All writes must generate a diff.
- Proposal → approval lifecycle must be preserved.

---

### 4. Deny-By-Default

PolicyEngine must:
- Enforce workspace boundary
- Enforce deny patterns
- Fail closed on error

---

### 5. Audit Requirements

Every tool must:
- Log allow
- Log deny
- Log structured metadata
- Never mutate silently

---

### 6. Git Discipline

Before committing:

```bash
git status
git diff
git diff --staged
```
**Hard rules:**

- Do not commit `.audit/`, `workspace/`, `__pycache__/`, `.env`, or local temp files.
- Keep commits small and single-purpose.
- If you change policy, gateway routing, audit logging, or execution behavior — you must add or update tests.
- Do not bypass `ToolGateway` for execution or file access.
- If modifying git policy/gateway/audit logic, add explicit deny-case tests.
---

### 7. Run Tests Locally

Before pushing:

```bash
python -m pytest -q
```
If you modify command execution or subprocess behavior, also verify:

```bash
grep -RIn "shell=True" agent_core tools policy audit tests
grep -RIn "subprocess\\.|os\\.system\\(|Popen\\(" agent_core tools policy audit tests
```
Do not invoke git via subprocess directly. Use GIT_RUN tool surface.
