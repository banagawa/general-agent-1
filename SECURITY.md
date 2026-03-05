
# Security Model

This document defines the threat model and enforcement guarantees of General Agent.

---

## Threat Model

This system assumes:

- Untrusted user input may reach tool layer.
- Accidental misuse is more likely than malicious attack.
- Command execution must not escalate beyond workspace.
- Writes must never occur without visibility.

This system does NOT currently defend against:
- OS-level privilege escalation
- Kernel-level attacks
- External network exploitation (no connectors implemented)

---

## Enforcement Layers

### 1. Workspace Boundary

All file access is constrained to WORKSPACE_ROOT.

Enforcement:
- Path canonicalization via resolve()
- relative_to() boundary check
- Fail closed on error

---

### 2. Deny Patterns

Access denied for:
- .env
- secrets
- credentials

---

### 3. Patch-Only Writes

- No full-file overwrite
- All writes diff-visible
- Explicit approval required
- Revocation enforced per invocation

---

### 4. Command Execution Controls

CMD_RUN enforces:

- Allowlisted commands only
- Subcommand validation
- argv-only execution
- shell=False
- Forced cwd to workspace
- Timeout enforcement
- Output truncation

Denied commands:
- bash
- sh
- cmd
- powershell
- curl
- wget
- Arbitrary interpreters

---

### Git Execution Controls (GIT_RUN)

Git operations are isolated behind a dedicated tool.

Restrictions:
- Only allowlisted subcommands permitted
- Unknown flags rejected
- No config override flags (-c, --git-dir, --work-tree, -C)
- No remote or branch operations (push, pull, fetch, clone, remote, checkout, switch, branch, merge, rebase, tag, submodule)
- No network access
- Workspace-bound execution only
- Mutating operations require capability token
- All attempts audited (allow + deny)

---
### 5. Audit Guarantees

Every tool invocation logs:

- action
- timestamp
- structured metadata
- allow or deny result

Audit log is append-only.


### 6. Structured Plan Gating (Planned)

Planned enforcement:
- No free-form execution
- Tool execution only from an approved deterministic PLAN
- Plan schema violations deny + audit
- Plan hash recorded in audit for traceability

---

## Fail-Closed Guarantee

If:
- Path resolution fails
- Policy check fails
- Token invalid (future)
- Timeout occurs
- Unexpected exception

The operation must deny and log.

---

## Revocation Model

Current:
- Global write revocation persisted on disk.

Planned:
- Tokenized capability model
- Expiry enforcement
- Revocation keyed by token ID

---

## Security Philosophy

The system is designed to:

- Minimize blast radius
- Make mutation visible
- Preserve auditability
- Prefer denial over uncertainty
- Avoid implicit privilege

Any change weakening these properties must be reviewed and documented.

---

## Reporting Issues

Security concerns should be documented as:

- Description
- Reproduction steps
- Expected behavior
- Actual behavior
- Proposed mitigation

Security changes must include:

- Policy update
- Audit update
- Documentation update
