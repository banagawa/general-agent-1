# Plan Artifact Ownership

Status: characterization guard

## Purpose

This document records the ownership model for plan lifecycle artifacts before any storage migration.

Plan artifacts are operational records produced by the agent while managing plan submit, approval, execution, failure, and summary flows.

They are not target project source files.

## Current location

Plan lifecycle artifacts currently live under the target worktree:

- `plans/pending/`
- `plans/approved/`
- `plans/executed/`
- `plans/failures/`
- `plans/summaries/`

The workspace fingerprint excludes `plans/`, so these files are already treated differently from source workspace content.

## Ownership classification

### Runtime history

These artifacts are runtime history:

- approved plans
- executed plans
- failure envelopes
- execution summaries

They should be preserved for review, traceability, and audit reconstruction.

### Runtime workflow state

These artifacts are runtime workflow state:

- pending plans
- pending approval metadata

They support the current plan lifecycle and should remain outside target project source.

## Current runtime location

New plan lifecycle artifacts are stored under:

`workspace/agent_runtime/<workspace_name>/plans/`

Structure:

- `agent_runtime/<workspace_name>/plans/pending/`
- `agent_runtime/<workspace_name>/plans/approved/`
- `agent_runtime/<workspace_name>/plans/executed/`
- `agent_runtime/<workspace_name>/plans/failures/`
- `agent_runtime/<workspace_name>/plans/summaries/`

This keeps:

- live app root clean
- target worktree clean
- runtime history persistent and reviewable

## Audit relationship

Audit events should reference plan artifacts using stable identifiers.

Preferred audit fields:

- `plan_hash`
- `plan_id`
- `artifact_path`
- `artifact_kind`

Audit events should not repeatedly embed full plan payloads when the plan artifact already exists as durable runtime history.

## Historical data migration

This change moves new plan lifecycle writes to the runtime-state root.

It does not automatically migrate historical plan artifacts that already exist under a target worktree.

A future runtime migration tool should handle historical data explicitly.

## Runtime history health monitoring

Runtime history health monitoring is implemented as read-only inspection.

The helper `get_runtime_history_health()` reports:

- runtime-state root
- whether the root exists
- total bytes
- file count
- warning reason codes

Warning reason codes:

- `RUNTIME_HISTORY_SIZE_WARNING`
- `RUNTIME_HISTORY_FILE_COUNT_WARNING`

The helper does not delete, compact, archive, migrate, or rewrite runtime history.

## Future runtime history operations

The following are intentionally not implemented yet:

- runtime export tool
- runtime archive tool
- runtime migration tool
- retention policy
- compaction policy
- integrity verification
- checksum verification

No cleanup, deletion, compaction, or retention enforcement should happen without an explicit future design.
