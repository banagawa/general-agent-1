# System State v1

This document describes the merged system state after Sprint H Slice 7, including Sprint G, pre-Sprint-H hardening, typed mutation, worktree-safe root separation, runtime-state ownership, and the workspace intelligence layer.

---

# Core Architecture

Execution pipeline:

Human → `task.plan` or `plan.submit` → `plan.approve` → `plan.execute` → Orchestrator → AgentLoop → PlanExecutor → execute_step → ToolGateway → PolicyEngine → Tool

All tool execution passes through ToolGateway.

Execution remains deterministic, approval-bound, and fail-closed.

Current root model:

- `app_root`: authoritative runtime/security-code root
- `workspace_root`: mutation boundary
- `execution_root`: command/test cwd
- `runtime_import_root`: imported runtime module source

Worktree execution requires explicit separation of runtime root and mutation root. `AGENT_APP_ROOT` may bind the authoritative app root so cwd does not redefine runtime identity.

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
- Sprint F controlled autonomy completed
- worktree-safe runtime/workspace root separation
- workspace intelligence is advisory only and never grants authority

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

Autonomy state:
- `task.autonomy` produces approval-bound pending plans
- autonomy budgets are enforced before submission
- rollback restores original file state on failure
- autonomy decisions emit audit events

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

# Current Development State

Sprint F is complete.

Sprint G deterministic improvement foundation is complete:
- execution outcomes are normalized through `CycleOutcome`.
- strategy records and proposals are inert data.
- registry writes are append-only JSONL.
- proposal generation is deterministic from execution outcomes.
- proposal integration is post-cycle only.
- proposal generation does not auto-install strategies.
- `TEST_RUN` supports explicit cwd modes: `workspace` and `app`.

Pre-Sprint-H hardening is complete:
- TEST_RUN allowlisting.
- approval-time mutation/file-state validation.
- path hygiene and capability-scope hardening.
- runtime-state ownership and runtime history health reporting.
- rollback boundary rechecks.
- root authority invariant tests.
- ToolGateway static guards.
- denial audit observability.
- workspace intelligence boundary guardrail.

Sprint H is complete through Slice 7:
- ArtifactID model.
- read-only workspace graph.
- dependency-aware impact analysis.
- ArtifactID lookup index.
- graph query helpers.
- static call graph mapping.
- function-level impact propagation.
- intelligent advisory test selection through `select_tests_for_changes(...)`.

Future strategy installation remains approval-gated and out of scope for the completed Sprint G foundation. Future workspace intelligence consumers must preserve the advisory-only boundary.

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
