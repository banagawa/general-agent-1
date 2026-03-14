# CONTRIBUTING.md

Status: Governing Contributor Guide

Before contributing read:

- SECURITY.md
- docs/anchors/security-invariants.md
- docs/anchors/architecture-contract.md
- docs/anchors/system-state-v1.md

---

## Non Negotiable Development Rules

### No Tool Bypass

All execution must pass through:

AgentLoop → ToolGateway → PolicyEngine → Tool

### No shell=True

Commands must be argv lists and executed with shell=False.

### Patch Only Writes

Never overwrite files directly.
All mutation must be diff-visible and approval gated.

### Deny By Default

PolicyEngine must enforce workspace boundaries and capability checks.

### Audit Everything

Every tool invocation must log:

- allow
- deny
- metadata

---

## Commit Discipline

Before committing:

git status
git diff
git diff --staged

Rules:

- commits must be small and focused
- do not commit audit artifacts
- do not commit workspace temp files