# Pre-Sprint-H Hardening Closeout v6

Status: complete

Purpose: record the hardening sequence merged after Sprint G and before Sprint H.

## Source PRs and commits

| PR | Merge commit | Area | Current-state meaning |
|---:|---:|---|---|
| #13 | `52c05fb` | TEST_RUN allowlist and mutation approval validation | Constrained TEST_RUN command shapes and validated mutation tool/file-state alignment at approval time. |
| #14 | `b706674` | Path validation, capability scope, storage characterization | Hardened path hygiene and scoped capability validation; characterized storage behavior. |
| #15 | `9213276` | Runtime-state ownership and fingerprint exclusion | Documented runtime-state ownership and added future fingerprint exclusion bridge. |
| #16 | `a6a61e5` | Runtime bookkeeping outside target worktree | Moved audit/capability/pending-patch runtime bookkeeping under workspace/agent_runtime/<workspace_name>. |
| #17 | `7f4a07a` | Runtime history ownership and health reporting | Moved plan lifecycle artifacts to runtime-state root and added report-only runtime history health. |
| #18 | `e67b610` | Rollback workspace boundary recheck | Rechecked rollback snapshot paths against workspace boundary before restore/delete. |
| #19 | `21eb805` | Root authority invariant tests | Proved cwd does not become workspace authority and app_root cannot become workspace_root. |
| #20 | `34bde3c` | ToolGateway chokepoint invariant guards | Guarded against direct filesystem, policy, or command execution paths outside ToolGateway. |
| #21 | `54745fb` | Denial audit observability | Verified representative denial paths emit audit events. |
| #22 | `49eabfc` | Workspace intelligence authority boundary | Documented advisory-only workspace intelligence before implementation. |


## Current architectural result

The hardening sequence stabilized runtime/workspace separation before workspace intelligence work began.

Current guarantees:

- `TEST_RUN` is allowlisted and may use only `cwd: "workspace"` or `cwd: "app"`.
- mutation tools are validated against file state before approval.
- plan paths and capability scopes fail closed on unsafe paths.
- runtime bookkeeping is outside the target worktree under `workspace/agent_runtime/<workspace_name>/`.
- plan lifecycle artifacts are runtime history, not source workspace content.
- runtime history health is report-only.
- rollback cannot restore or delete outside workspace even if snapshot data is poisoned.
- cwd cannot become runtime or workspace authority.
- ToolGateway remains the chokepoint.
- denial paths are audited.

## Non-goals

- no policy expansion.
- no capability expansion beyond explicitly documented tools.
- no autonomous retries.
- no runtime history cleanup or retention enforcement.
- no execution blocking based on runtime health warnings.

## Validation

Each hardening PR recorded validation in its PR body. This closeout is documentation-only.
