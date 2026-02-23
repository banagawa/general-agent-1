
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
