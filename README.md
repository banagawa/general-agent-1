# General Agent 1

A deterministic, policy-enforced software agent for repository work.

The system preserves five core invariants:

- ToolGateway is the single execution choke point
- deny-by-default policy enforcement
- workspace boundary isolation
- typed, reviewable file mutations:
  - PATCH_APPLY (existing-file modification only)
  - PATCH_EDIT (deterministic existing-file text edit only)
  - FILE_CREATE (new-file creation only)

- append-only audit logging

Execution remains fail-closed and approval-bound.

---

# Current Operating Model

The runtime now supports two approved front doors:

1. `task.plan:<task>`
2. `plan.submit:<json>`

Both feed the same approval-bound execution path.

3. `task.autonomy:<json>`

`task.autonomy` supports:
- `MANUAL`
- `ASSISTED`
- `BOUNDED_AUTONOMOUS`

Bounded autonomy remains approval-bound and feature-flag gated.

Sprint F is complete.

Sprint G is complete. It added deterministic outcome normalization, inert strategy/proposal records, append-only strategy registry writes, deterministic proposal generation, and a post-cycle proposal hook. Strategy installation remains explicitly out of scope and approval-gated for any future work.

Pre-Sprint-H hardening is complete. It added TEST_RUN allowlisting, approval-time mutation validation, path/capability hardening, runtime-state ownership, runtime history health reporting, rollback boundary rechecks, root authority invariant tests, ToolGateway static guards, denial audit observability, and the workspace-intelligence authority boundary.

Sprint H is complete through Slice 7. The workspace intelligence layer now includes ArtifactIDs, workspace graph construction, dependency-aware impact analysis, ArtifactID lookups, graph query helpers, static call graph mapping, function-level impact propagation, and intelligent advisory test selection.

Current Sprint G/H behavior:
- execution outcomes are normalized through `CycleOutcome`
- strategies and proposals are inert data only
- strategy registry records are append-only JSONL
- proposal generation is deterministic from execution outcomes
- proposal hook is post-cycle only and does not auto-install strategies
- workspace intelligence is advisory only and never grants authority
- intelligent test selection recommends tests and can recommend full-suite fallback; it does not run tests

Runtime test execution supports explicit TEST_RUN cwd selection:
- `cwd: "workspace"` tests the configured workspace/worktree
- `cwd: "app"` tests the runtime application root

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

Before submitting, approving, or executing a workspace-targeted plan from the outer app repo, bind the workspace root to the intended worktree:

```bash
cd /c/Users/Bryan/Documents/general-agent-1
unset PYTHONPATH
export AGENT_WORKSPACE_ROOT="$PWD/workspace/general-agent-1-dev"
```

Verify the binding before running plan commands:

```bash
python - <<'PY'
from pathlib import Path
from sandbox.mounts import get_workspace_root

ws = Path(get_workspace_root())
print(ws)
print((ws / "docs").exists())
print((ws / "tests").exists())
PY
```

Do not rely on the default workspace root for repo-targeted plans; the default may resolve to the workspace container directory rather than the `general-agent-1-dev` worktree.

Simple test example:

```text
plan.submit:{"plan_id":"example","steps":[{"step_id":1,"tool":"TEST_RUN","capability":"test.run","args":{"argv":["python","-m","pytest","-q"],"timeout_seconds":120,"cwd":"workspace"}}]}
```

PATCH_APPLY example:

```text
plan.submit:{"plan_id":"replace-readme-note","steps":[{"step_id":1,"tool":"PATCH_APPLY","capability":"patch.apply","args":{"path":"README.md","new_content":"# General Agent 1\n"}}]}
```

PATCH_EDIT example:

```text
plan.submit:{"plan_id":"edit-readme-note","steps":[{"step_id":1,"tool":"PATCH_EDIT","capability":"patch.edit","args":{"path":"README.md","edits":[{"old_text":"patch-only file writes","new_text":"patch-only typed file mutation"}]}}]}
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

# Runtime Root Model

The runtime distinguishes four roots:

- `app_root`: authoritative outer runtime and security-code root
- `workspace_root`: mutation boundary used by file, git, and plan artifacts
- `execution_root`: current working directory used for command or test execution
- `runtime_import_root`: source location for imported runtime modules

`app_root` and `workspace_root` must never collapse. `workspace_root` must be anchored to `app_root` or explicitly configured, not derived from the current working directory. `AGENT_APP_ROOT` may be used to bind the authoritative runtime root during worktree-safe execution.

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
- `PATCH_EDIT` → `FS_EDIT_PATCH`
- `FILE_CREATE` → `FS_CREATE_FILE`

`TEST_RUN` may choose only `cwd: "workspace"` or `cwd: "app"`; raw cwd paths are forbidden.

---

# Typed Mutation Model

Three write tools now exist and they stay distinct:

- `PATCH_APPLY`
  - whole-file replacement only
  - target file must already exist
  - exact-path scoped token
  - audited

- `PATCH_EDIT`
  - anchored exact-text replacement only
  - target file must already exist
  - supports `old_text`, `new_text`, optional `occurrence`
  - optional `expected_file_sha256_before`
  - exact-path scoped token
  - audited

- `FILE_CREATE`
  - new-file creation only
  - target file must not already exist
  - parent directory must already exist
  - exact-path scoped token
  - audited

`PATCH_EDIT` is not:
- regex editing
- fuzzy matching
- AST patching
- line-number-only editing
- silent fallback to whole-file rewrite

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

# Execution Summary Shape

Execution summaries now expose:

- `modified_paths`
- `patch_apply_paths`
- `patch_edit_paths`

`changed_paths` is retained as a compatibility alias for `modified_paths`.

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

Mutation events now include:

- `PATCH_EDIT_ALLOWED`
- `PATCH_EDIT_DENIED`
- `PATCH_EDIT_EXECUTED`

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
# Workspace Intelligence Layer

Sprint H is complete through Slice 7.

Current advisory APIs include:

- `ArtifactID` parsing/formatting/validation.
- `build_workspace_graph(...)`.
- `WorkspaceGraph.find_artifact(...)` and convenience query helpers.
- `WorkspaceGraph.calls_from(...)` and `WorkspaceGraph.called_by(...)`.
- `impacted_tests_for_paths(...)`.
- `impacted_tests_for_modules(...)`.
- `impacted_tests_for_functions(...)`.
- `select_tests_for_changes(...)` returning `TestSelection`.

Workspace intelligence is advisory planner data only. It may recommend impacted tests or fallback to the full suite. It does not execute tests, mutate plans, grant permissions, bypass policy, or authorize workspace mutation.

---
# Project Status

| Area | Status |
|---|---|
| Sprint A | Complete |
| Sprint B | Complete |
| Sprint C | Complete |
| Sprint D | Complete |
| Sprint E | Complete |
| Sprint F | Complete |
| Sprint G | Complete |
| Pre-Sprint-H hardening | Complete |
| Sprint H | Complete through Slice 7 |

---

# Current Documentation Index

- `docs/anchors/current-state-ledger-v6.md` records merged PR/commit state through Sprint H Slice 7.
- `docs/sprints/pre-sprint-h-hardening-closeout-v6.md` records the hardening sequence after Sprint G.
- `docs/sprints/sprint-h-closeout-v6.md` records Sprint H Slice 1 through Slice 7.
- `docs/non-python-reconciliation-inventory-v6.md` records the non-Python documentation reconciliation scope.
