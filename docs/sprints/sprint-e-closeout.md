# Sprint E Closeout

Deterministic Dev Loop + Planner-Gated Entry

## Goal

Complete Sprint E without weakening the security model.

Sprint E scope, as merged, was:

- deterministic approved-plan execution
- execution summaries and failure envelopes
- replay denial
- workspace drift binding at approval time
- planner-assisted plan creation through `task.plan`

The result is a full proposal → approval → execution loop, not just an execute/test/diff slice.

---

# Architecture Invariants Preserved

The following invariants remained intact through Sprint E:

- ToolGateway choke point
- PolicyEngine deny-by-default
- workspace boundary enforcement
- patch-only file writes
- append-only audit log
- fail-closed execution

Merged execution path:

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

Planner integration did not introduce a bypass.

---

# What Sprint E Added

## 1) Deterministic execution loop

`plan.execute` now runs a bounded deterministic step loop.

Per step:
1. verify execution remains inside the transaction budget
2. issue a step-scoped capability token
3. execute the step through ToolGateway
4. record the step result
5. accumulate changed paths and test outcomes
6. derive final execution status

Outputs:
- execution marker
- execution summary
- optional failure envelope

## 2) Replay denial

A previously executed approved plan cannot be executed again.

Replay attempt outcome:
- execution denied
- `PLAN_EXECUTION_REPLAY_DENIED` logged

## 3) Workspace drift binding

Approval now records a deterministic workspace fingerprint.

Execution verifies the current workspace fingerprint before the run begins.

If drift is detected:
- execution is denied before step execution
- `PLAN_EXECUTION_DRIFT_DENIED` logged
- new approval is required

## 4) Planner front door

`task.plan:<task>` was added.

Flow:
- raw task converted into `TaskSpec`
- planner generates PLAN JSON
- plan metadata is attached
- plan is validated
- pending plan is stored
- normal approval path still required

Planner metadata includes:
- planner source: `deterministic` or `llm`
- intent goal
- success criteria

The planner may propose. It may not execute.

---

# Plan Lifecycle After Merge

## Submit or plan

Two valid creation paths now exist:

### Human-authored plan
```text
plan.submit:<json>
```

### Planner-authored proposal
```text
task.plan:<task>
```

Both end in a pending plan artifact:

- `plans/pending/<plan_hash>.json`

## Approve

```text
plan.approve:<plan_hash>
```

Approval writes:

- `plans/approved/<plan_hash>.json`
- `plans/approved/<plan_hash>.meta.json`

Approval metadata includes:

- `plan_hash`
- `workspace_fingerprint`
- `drift_check_enabled`
- `approved_at`

## Execute

```text
plan.execute:<plan_hash>
```

Execution writes:

- `plans/executed/<plan_hash>.json`
- `plans/summaries/<plan_hash>-<tx_id>.json`

On failure it also writes:

- `plans/failures/<plan_hash>-<tx_id>.json`

---

# Summary Artifact Shape

Sprint E made summaries first-class runtime artifacts.

Summary fields include:

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

`requires_new_approval` is false only on `SUCCESS`.

---

# Failure Envelope Shape

Failure envelopes are written for non-success outcomes.

Fields include:

- `plan_hash`
- `tx_id`
- `result_status`
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

This captures enough state to explain why the run stopped without pretending the plan completed successfully.

---

# Audit Events Observed in the Sprint E State

Execution lifecycle:
- `PLAN_CREATED`
- `PLAN_APPROVED`
- `PLAN_EXECUTION_STARTED`
- `PLAN_SUMMARY_RECORDED`
- `PLAN_EXECUTION_FINISHED`
- `PLAN_FAILURE_ENVELOPE_RECORDED`
- `PLAN_EXECUTION_FAILED`
- `PLAN_EXECUTION_REPLAY_DENIED`
- `PLAN_EXECUTION_DRIFT_DENIED`

Planner lifecycle:
- `PLANNER_REQUESTED`
- `PLANNER_PLAN_CREATED`
- `PLANNER_DENIED`

This is materially richer than the earlier Sprint E docs that only described start/finish/failure.

---

# Limits Enforced

Sprint E enforces bounded execution at runtime.

Current execution limits in code:
- max steps per execution: `25`
- max execution seconds: `120`

If limits are violated, execution fails closed.

---

# Verification Coverage Reflected by the Merged State

The merged repository state shows Sprint E covering these behaviors:

## Success path
- approved plan executes
- summary written
- executed marker finalized

## Failure path
- failure status classified
- summary still written
- failure envelope written
- executed marker finalized with non-success status

## Replay denial
- second execution attempt rejected

## Drift denial
- changed workspace after approval rejects execution

## Planner path
- `task.plan` creates a validated pending plan
- planner source is recorded
- approval still required

---

# Sprint E Result

Sprint E is complete on `main`.

Sprint E now means:

- controlled task-to-plan entry
- explicit approval
- deterministic execution
- replay denial
- workspace drift binding
- summary artifacts
- failure envelopes
- audit-complete lifecycle records

Next sprint: Sprint F — Controlled Autonomy Mode

---

# Post-Closeout Hardening Follow-Through

After Sprint E closeout, the execution path was hardened further without weakening the governing invariants.

Added after closeout:

## 1) Central preflight gate

Execution now passes through a single preflight path that validates:

- execution request format
- approved plan presence
- approval metadata presence and schema
- canonical plan hash match
- workspace drift state

## 2) Explicit execution state model

Execution now uses an explicit state model:

- `APPROVED`
- `IN_FLIGHT`
- `EXECUTED`
- `FAILED`

Allowed transitions:

- `APPROVED -> IN_FLIGHT`
- `IN_FLIGHT -> EXECUTED`
- `IN_FLIGHT -> FAILED`

All other transitions are denied.

## 3) Centralized deny surface

Denials are now emitted through a shared deny path with standardized reason codes and append-only audit payloads.

Representative reason codes include:

- `PLAN_REPLAY_DENIED`
- `PLAN_EXECUTION_DRIFT_DENIED`
- `PLAN_HASH_MISMATCH`
- `INVALID_PLAN_HASH`

## 4) Stricter ingress validation

Execution request and approval metadata validation were tightened to reject malformed identifiers, unknown metadata fields, and invalid field types before execution begins.

## 5) Concurrency and crash hardening

Additional test coverage now verifies:

- only one concurrent execution of the same approved plan succeeds
- replay denial remains atomic
- workspace drift denial emits searchable reason-coded audit records
- approved-plan mutation after execution starts does not alter the already-started execution outcome

This hardening pass preserved the same core model while making the execution control plane more explicit and test-backed.
