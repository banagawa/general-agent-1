# System State v1

This document describes the merged system state after Sprint E.

---

# Core Architecture

Execution pipeline:

Human → `task.plan` or `plan.submit` → `plan.approve` → `plan.execute` → Orchestrator → AgentLoop → PlanExecutor → execute_step → ToolGateway → PolicyEngine → Tool

All tool execution passes through ToolGateway.

Execution remains deterministic, approval-bound, and fail-closed.

---

# Security Invariants

The system currently maintains these invariants:

- ToolGateway is the single execution choke point
- deny-by-default enforcement
- workspace boundary isolation
- typed file mutation model:
  - PATCH_APPLY modifies existing files only
  - FILE_CREATE creates new files only
- append-only audit logging
- approved-plan-only execution
- workspace-fingerprint drift denial before execution
- capability-scoped step execution
- central preflight validation before execution
- explicit execution state transitions
- single-use execution per approval
- reason-coded deny audit

---

# Planner State

The runtime now exposes a planner front door:

- `task.plan:<task>`

Planner flow:

`task.plan` → `TaskSpec` → planner → validated pending plan

Planner source may be:

- `deterministic`
- `llm`

Planner output is still just a proposal.
It does not execute tools, approve plans, or bypass policy.

Planner metadata recorded on submitted plans includes:

- planner source
- intent goal
- success criteria

---

# Plan Execution Model

Execution requires an approved plan.

Supported commands:

- `task.plan`
- `plan.submit`
- `plan.approve`
- `plan.execute`

Execution lifecycle:

`task.plan` or `plan.submit`  
→ pending plan created  
→ `plan.approve` records approval metadata and workspace fingerprint  
→ `plan.execute` runs central preflight validation  
→ preflight validates approval metadata, hash match, and drift state  
→ execution transitions `APPROVED -> IN_FLIGHT`  
→ deterministic step execution begins  
→ execution transitions to `EXECUTED` or `FAILED`

Execution artifacts:

- `plans/pending/<plan_hash>.json`
- `plans/approved/<plan_hash>.json`
- `plans/approved/<plan_hash>.meta.json`
- `plans/executed/<plan_hash>.json`
- `plans/summaries/<plan_hash>-<tx_id>.json`
- `plans/failures/<plan_hash>-<tx_id>.json`

---

# Approval and Drift Binding

At approval time the system writes:

- `plan_hash`
- `plan_id`
- `workspace_fingerprint`
- `drift_check_enabled`
- `approved_at`
- `approval_source`

At execution time the current workspace fingerprint is recomputed.

If fingerprints differ:
- execution is denied
- `PLAN_EXECUTION_DRIFT_DENIED` is logged
- a new approval cycle is required

---

# Execution Status Model

Observed execution result classes include:

- `SUCCESS`
- `FAILED`
- `TEST_FAILURE`
- `PATCH_REJECTED`
- `PLAN_INVALID`
- `REPLAY_DENIED`
- `WORKSPACE_DRIFT_DENIED`
- `STEP_LIMIT_EXCEEDED`
- `TIME_BUDGET_EXCEEDED`
- `CAPABILITY_DENIED`

Execution summaries record:

- `plan_hash`
- `tx_id`
- `execution_status`
- `started_at`
- `finished_at`
- `steps_attempted`
- `steps_completed`
- `test_summary`
- `changed_paths`
- `requires_new_approval`
- `intent`

Failure envelopes record at least:

- `plan_hash`
- `tx_id`
- `failure_class`
- `failing_step_id`
- `tool`
- `exit_code`
- `timed_out`
- `changed_paths`
- `error`
- `test_summary`
- `requires_new_approval`
- `intent`

---

# Audit Lifecycle

Core lifecycle events:

- `PLAN_CREATED`
- `PLAN_APPROVED`
- `PLAN_EXECUTION_STARTED`
- `PLAN_SUMMARY_RECORDED`
- `PLAN_EXECUTION_FINISHED`
- `PLAN_FAILURE_ENVELOPE_RECORDED`
- `PLAN_EXECUTION_FAILED`
- `DENY`

Representative deny reason codes:

- `PLAN_REPLAY_DENIED`
- `PLAN_EXECUTION_DRIFT_DENIED`
- `PLAN_HASH_MISMATCH`
- `INVALID_PLAN_HASH`

Audit logs are append-only.

---

# Sprint Status

| Sprint | Status |
|---|---|
| Sprint A | Complete |
| Sprint B | Complete |
| Sprint C | Complete |
| Sprint D | Complete |
| Sprint E | Complete |

---

# Next Phase

Sprint F — Controlled Autonomy Mode

That phase is next. It is not the current merged behavior.
