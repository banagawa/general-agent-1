# Runtime State Ownership Contract

Status: characterization guard

## Purpose

This document records the runtime-state ownership model currently implied by the codebase.

It does not migrate storage.
It does not change runtime behavior.
It exists so future migrations can be designed deliberately.

## Workspace state

Workspace state is the protected project content that participates in workspace fingerprinting.

Examples:

- source code
- tests
- documentation
- configuration

When these files change, workspace fingerprint drift should be visible.

## Execution history

Execution history is stored under `plans/`.

Examples:

- `plans/pending/`
- `plans/approved/`
- `plans/executed/`
- `plans/failures/`
- `plans/summaries/`

The current fingerprint implementation excludes `plans/` from workspace fingerprinting.

This means execution history is stored inside the workspace tree, but it is not treated as protected workspace content for drift detection.

## Runtime bookkeeping

Runtime bookkeeping is stored under the visible runtime-state root.

Examples:

- `agent_runtime/<workspace_name>/audit/audit.jsonl`
- `agent_runtime/<workspace_name>/capabilities/capability_tokens.json`
- `agent_runtime/<workspace_name>/capabilities/capability_revocations.json`
- `agent_runtime/<workspace_name>/pending/pending_patches.json`

These files are runtime records, not source workspace content.

## Runtime-state root

The runtime-state root is a visible sibling runtime area under the workspace container:

`workspace/agent_runtime/<workspace_name>`

For the current development worktree, that means:

`workspace/agent_runtime/general-agent-1-dev`

The helper `get_runtime_state_root()` exposes this location without moving current stores.

This keeps the live app root clean and keeps runtime bookkeeping outside the target worktree.

## Runtime-state fingerprint exclusion

The workspace fingerprint excludes `.runtime_state/` for compatibility with the earlier bridge design.

The preferred runtime-state location is now outside the target worktree at `workspace/agent_runtime/<workspace_name>`, so future runtime bookkeeping should not participate in target workspace fingerprints at all.

Audit logs, capability token state, and pending patch state now use the runtime-state root.

## Migration result

Runtime bookkeeping now uses the explicit runtime-state root.

The migration target is `workspace/agent_runtime/<workspace_name>/`, not `workspace_root/.audit`.

Because runtime bookkeeping is outside the target worktree, runtime writes do not create target workspace drift while source files remain protected by drift detection.

## Plan lifecycle artifacts

Plan lifecycle artifacts are stored under the runtime-state root:

`workspace/agent_runtime/<workspace_name>/plans/`

Examples:

- `plans/pending/`
- `plans/approved/`
- `plans/executed/`
- `plans/failures/`
- `plans/summaries/`

Historical plan artifacts that already exist under a target worktree are not migrated automatically.

The ownership details and future migration notes are documented in `docs/plan_artifact_ownership.md`.

## Future runtime history operations

Future work should include read-only disk/history health checks before any cleanup or retention behavior.

Documented but not implemented yet:

- runtime export tool
- runtime archive tool
- runtime migration tool
- retention policy
- compaction policy
- integrity verification
- checksum verification
- disk usage health monitoring

Initial health checks should be warning-only and should not delete, compact, archive, or migrate data automatically.

## Non-goals

This contract does not:

- change plan storage
- add a new subsystem
