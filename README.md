# General Agent 1

A deterministic, policy-enforced autonomous software agent.

The system is built around strict architectural invariants:

- ToolGateway is the single execution choke point
- Deny-by-default policy enforcement
- Workspace boundary isolation
- Patch-only file writes
- Append-only audit logging

Execution is deterministic and policy controlled.

---

# Architecture Overview

Execution pipeline:

AgentLoop
 → PlanExecutor
 → execute_step
 → ToolGateway
 → PolicyEngine
 → Tool

All tools are executed through the ToolGateway which enforces capability tokens and policy checks.

---

# Structured Planning (Sprint D — Implemented)

All execution now requires a deterministic PLAN artifact.

Execution flow:

1. Submit a structured plan
2. Approve the plan
3. Execute the approved plan

Commands:

Submit plan:
plan.submit:<json>

Approve plan:
plan.approve:<plan_hash>

Execute plan:
plan.execute:<plan_hash>

Example:

plan.submit:{"plan_id":"example","steps":[{"step_id":1,"tool":"TEST_RUN","capability":"test.run","args":{"argv":["python","--version"]}}]}

Response:
PLAN_HASH=<hash>
STEPS=1
STATUS=PENDING_APPROVAL

---

# Raw Execution Protection

Direct execution is blocked.

Examples:
cmd.run: echo hello
update file: file.txt: content
propose patch: file.txt: content

Response:
DENIED: use PLAN

---

# Capability Model

Each tool execution requires a capability token.

Tokens are:
- short-lived
- scoped
- fail-closed

Tokens are issued automatically when executing approved plan steps.

---

# Audit Events

PLAN_CREATED
PLAN_APPROVED
PLAN_EXECUTION_STARTED
PLAN_EXECUTION_FINISHED
PLAN_EXECUTION_DENIED
PLAN_EXECUTION_FAILED

Audit logs are append-only.

---

# Development Workflow

Run agent:

python main.py "<task>"

Example:

python main.py "plan.submit:{...}"

---

# Project Status

| Sprint | Status |
|------|------|
Sprint A | Complete |
Sprint B | Complete |
Sprint C | Complete |
Sprint D | Complete |

---

# Next Phase

Sprint E: Deterministic development loops.