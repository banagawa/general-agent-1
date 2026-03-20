# General Agent 1

A deterministic, policy-enforced software agent for repository work.

The system preserves five core invariants:

- ToolGateway is the single execution choke point
- deny-by-default policy enforcement
- workspace boundary isolation
- patch-only file writes
- append-only audit logging

Execution remains fail-closed and approval-bound.

---

# Current Operating Model

The runtime now supports two approved front doors:

1. `task.plan:<task>`
2. `plan.submit:<json>`

Both feed the same approval-bound execution path.

Execution spine:

Human
→ `task.plan` or `plan.submit`
→ `plan.approve`
→ `plan.execute`
→ Orchestrator
→ AgentLoop
→ PlanExecutor
→ execute_step
→ ToolGateway
→ PolicyEngine
→ Tool Implementation

No tool executes outside ToolGateway.

---

# Command Surface

## 1) Planner front door

Use `task.plan` when the input is a human task rather than hand-authored PLAN JSON.

Example:

```text
task.plan:add a smoke test for planner denial on invalid JSON output
```

Behavior:

- task is normalized into `TaskSpec`
- planner generates PLAN JSON
- generated plan is validated
- validated plan is stored as pending
- response returns `PLAN_HASH`, `STEPS`, and `STATUS=PENDING_APPROVAL`

Planner metadata is recorded on the plan:

- planner source: `deterministic` or `llm`
- intent goal
- success criteria

## 2) Manual structured plan

Use `plan.submit` when you want to submit explicit PLAN JSON.

Example:

```text
plan.submit:{"plan_id":"example","steps":[{"step_id":1,"tool":"TEST_RUN","capability":"test.run","args":{"argv":["python","--version"]}}]}
```

## 3) Approval

```text
plan.approve:<plan_hash>
```

Approval writes the approved artifact and approval metadata, including:

- `plan_hash`
- `plan_id`
- `workspace_fingerprint`
- `drift_check_enabled`
- `approved_at`
- `approval_source`

## 4) Execution

```text
plan.execute:<plan_hash>
```

Execution is denied unless preflight succeeds.

Preflight validates:

- execution request shape
- plan identifier format
- approved plan presence
- approval metadata presence and schema
- canonical plan hash match
- workspace drift state

If preflight succeeds, execution transitions through the explicit execution state model:

- `APPROVED`
- `IN_FLIGHT`
- `EXECUTED` or `FAILED`

---

# Raw Execution Protection

Direct execution remains blocked.

Examples:

```text
cmd.run: echo hello
update file: file.txt: content
propose patch: file.txt: content
```

Response:

```text
DENIED: use PLAN
```

---

# Capability Model

Each tool execution requires a short-lived scoped capability token.

Current step-to-capability mapping:

- `TEST_RUN` → `CMD_RUN`
- `GIT_RUN` → `GIT_RUN`
- `PATCH_APPLY` → `FS_WRITE_PATCH`

Tokens are issued per approved step during execution.

---

# Sprint E Outcome

Sprint E is complete on `main`.

Sprint E now includes both layers:

## Deterministic execution loop

- approved-plan-only execution
- deterministic step loop
- bounded execution time
- replay denial
- execution summaries
- failure envelopes

## Planner-assisted entry

- `task.plan` command surface
- `TaskSpec` normalization
- deterministic planner fallback
- optional LLM planner path
- planner remains proposal-only and cannot execute tools

This keeps planning assistance inside the same approval and execution controls.

---

# Execution Artifacts

Artifacts written under `workspace/plans`:

- `plans/pending/<plan_hash>.json`
- `plans/approved/<plan_hash>.json`
- `plans/approved/<plan_hash>.meta.json`
- `plans/executed/<plan_hash>.json`
- `plans/summaries/<plan_hash>-<tx_id>.json`
- `plans/failures/<plan_hash>-<tx_id>.json`

---

# Audit Lifecycle

Core lifecycle events now include:

- `PLAN_CREATED`
- `PLAN_APPROVED`
- `PLAN_EXECUTION_STARTED`
- `PLAN_SUMMARY_RECORDED`
- `PLAN_EXECUTION_FINISHED`
- `PLAN_FAILURE_ENVELOPE_RECORDED`
- `PLAN_EXECUTION_FAILED`
- `DENY`

Important denial reason codes now include:

- `PLAN_REPLAY_DENIED`
- `PLAN_EXECUTION_DRIFT_DENIED`
- `PLAN_HASH_MISMATCH`
- `INVALID_PLAN_HASH`

Planner events:

- `PLANNER_REQUESTED`
- `PLANNER_PLAN_CREATED`
- `PLANNER_DENIED`

Audit logs remain append-only.
---
# Execution Hardening State

Post-Sprint-E hardening now includes:

- central preflight gate before execution
- atomic replay protection
- explicit execution state transitions
- centralized deny reasons and audit payloads
- stricter execution input and approval-metadata validation
- concurrent replay coverage
- documented crash semantics for `IN_FLIGHT`

Current execution policy is single-use per approval.
Once a plan enters `IN_FLIGHT`, that approval is consumed.
A rerun requires explicit new approval.
---

# Project Status

| Sprint | Status |
|---|---|
| Sprint A | Complete |
| Sprint B | Complete |
| Sprint C | Complete |
| Sprint D | Complete |
| Sprint E | Complete |

---

# Next Phase

Sprint F: Controlled Autonomy Mode

That phase is not described here as merged runtime behavior.
