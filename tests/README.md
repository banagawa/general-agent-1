# Test Guide

Status: current through Sprint H Slice 7

Run the full suite:

```bash
python -m pytest -q
```

## Current test areas

### Core control plane

- ToolGateway chokepoint invariants.
- deny-by-default policy behavior.
- capability token validation and revocation.
- workspace boundary enforcement.
- approval-bound plan execution.
- replay and drift denial.
- execution summaries and failure envelopes.
- append-only audit behavior.

### Typed mutation model

- `PATCH_APPLY`: existing-file whole replacement only.
- `PATCH_EDIT`: existing-file anchored exact-text edit only.
- `FILE_CREATE`: new-file creation only.

Mutation tests should preserve the create/modify split. Do not collapse these tools into one generic write path.

### Runtime/workspace separation

- `app_root` is runtime/security-code authority.
- `workspace_root` is the mutation boundary.
- `execution_root` is command/test cwd only.
- `runtime_import_root` is import-source authority.
- `TEST_RUN` may use only `cwd: "workspace"` or `cwd: "app"`.

### Sprint G

Sprint G tests cover deterministic improvement-engine data behavior:

- `CycleOutcome` normalization.
- inert strategy models.
- append-only strategy registry.
- deterministic proposal generation.
- post-cycle proposal integration.

Strategy proposals must remain inert and must not execute tools, mutate policy, install themselves, or expand autonomy.

### Pre-Sprint-H hardening

Hardening tests cover:

- TEST_RUN allowlisting.
- approval-time mutation/file-state validation.
- path hygiene and capability-scope hardening.
- runtime-state ownership.
- runtime history health reporting.
- rollback boundary rechecks.
- root authority invariants.
- ToolGateway static guards.
- denial audit observability.

### Sprint H workspace intelligence

Sprint H tests cover:

- ArtifactID validation.
- workspace graph construction.
- dependency-aware impact selection.
- ArtifactID lookup.
- graph query helpers.
- static call graph extraction.
- function-level impact propagation.
- intelligent advisory test selection.
- workspace intelligence authority boundary.

Workspace intelligence tests must preserve the advisory-only invariant. Graph results may recommend impacted files or tests, but must not grant permission, bypass policy, execute tests, mutate plans, or authorize workspace mutation.
