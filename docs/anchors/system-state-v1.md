# System State v1

This document describes the merged system state after Sprint E plus the current typed mutation model.

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
  - PATCH_EDIT performs deterministic existing-file text edits only
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

# Typed Mutation Model

Two mutation tools are live and distinct.

## PATCH_APPLY

- whole-file replacement only
- target file must already exist
- exact-path scoped token
- audited

## PATCH_EDIT

- anchored exact-text replacement only
- target file must already exist
- each edit item requires:
  - `old_text`
  - `new_text`
- each edit item may include:
  - `occurrence`
- step may include:
  - `expected_file_sha256_before`
- exact-path scoped token
- audited

`PATCH_EDIT` is not:
- regex editing
- fuzzy matching
- AST patching
- line-number-only editing
- fallback whole-file rewrite

Ambiguity behavior:

- 0 matches denies
- 1 exact match applies
- repeated exact matches without `occurrence` denies
- out-of-range `occurrence` denies

Atomicity behavior:

- multi-edit steps apply in declared order to progressively updated in-memory content
- if any edit fails, the whole step denies and nothing is written

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
- `modified_paths`
- `patch_apply_paths`
- `patch_edit_paths`
- `changed_paths` (compatibility alias of `modified_paths`)
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
- `modified_paths`
- `patch_apply_paths`
- `patch_edit_paths`
- `changed_paths` (compatibility alias of `modified_paths`)
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

Typed mutation audit events include:

- `PATCH_EDIT_ALLOWED`
- `PATCH_EDIT_DENIED`
- `PATCH_EDIT_EXECUTED`

---

# Current Limits

Current runtime limits in code:

- maximum steps per plan validation: `25`
- maximum steps per execution: `25`
- maximum execution seconds: `120`

If limits are exceeded, execution fails closed.

---

# Current Non-Goals

- no uncontrolled autonomy
- no background execution
- no planner-driven execution bypass
- no silent permission escalation
- no out-of-workspace mutation
