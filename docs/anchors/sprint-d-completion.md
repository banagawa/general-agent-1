# Sprint D --- Structured Plan Artifact (Completion Plan)

## Objective

Introduce a deterministic execution gate where all tool execution must
flow through an approved PLAN artifact.

No tool execution may occur until: 1. A plan is submitted 2. The plan is
validated 3. The plan hash is generated 4. The plan is explicitly
approved

------------------------------------------------------------------------

# Core Security Invariant

All execution MUST flow through:

PLAN → APPROVAL → EXECUTION

Direct tool execution is denied.

Fail closed if: - schema invalid - plan not approved - step violates
capability scope

------------------------------------------------------------------------

# PLAN Artifact

## Deterministic Schema

Example:

{ "version": 1, "steps": \[ { "id": "step1", "tool": "git.run", "args":
{ "cmd": "status" }, "capability": "repo_read" } \] }

Constraints:

  Field        Rule
  ------------ --------------------
  version      integer
  steps        ordered list
  id           unique
  tool         allowlisted tool
  args         parsed object only
  capability   required

Validation must fail closed.

------------------------------------------------------------------------

# Plan Hash

Plan hash guarantees immutability.

plan_hash = SHA256(canonical_json(plan))

Canonicalization rules:

-   sorted keys
-   no whitespace variance
-   UTF‑8 encoding

Hash must be stable.

------------------------------------------------------------------------

# Commands

## plan.submit

Creates a pending plan.

plan.submit `<json>`{=html}

Flow:

parse_plan() validate_plan() hash = compute_plan_hash(plan)
store_pending_plan(hash, plan)

Audit event:

PLAN_CREATED

Return:

PLAN_HASH=`<hash>`{=html} STEPS=`<count>`{=html} STATUS=PENDING_APPROVAL

------------------------------------------------------------------------

# plan.approve

Approves a pending plan.

plan.approve `<plan_hash>`{=html}

Flow:

load_pending(hash) mark_plan_approved(hash)

Audit event:

PLAN_APPROVED

Return:

PLAN_APPROVED `<hash>`{=html}

------------------------------------------------------------------------

# plan.execute

Executes a plan only if approved.

plan.execute `<plan_hash>`{=html}

Flow:

load_plan(hash)

if not approved: audit PLAN_EXECUTION_DENIED return deny

audit PLAN_EXECUTION_STARTED

for step in plan.steps: execute_step(gateway, step)

audit PLAN_EXECUTION_FINISHED

------------------------------------------------------------------------

# execute_step()

All tools must route through this function.

Example:

def execute_step(gateway, step):

    verify_capability(step.capability)

    result = gateway.execute(
        tool=step.tool,
        args=step.args
    )

    return result

------------------------------------------------------------------------

# Raw Execution Denial

Until Sprint E, all direct execution paths must deny.

Examples:

cmd.run → DENIED: use PLAN\
git.run → DENIED: use PLAN\
patch.apply → DENIED: use PLAN

Only allowed path:

plan.execute

------------------------------------------------------------------------

# Plan Store

Minimal implementation:

plans/ pending/ approved/

Example:

plans/pending/`<hash>`{=html}.json plans/approved/`<hash>`{=html}.json

Approval moves file:

pending → approved

------------------------------------------------------------------------

# Audit Events

Required lifecycle:

  Event                     Data
  ------------------------- ---------------
  PLAN_CREATED              hash
  PLAN_APPROVED             hash
  PLAN_EXECUTION_DENIED     hash + reason
  PLAN_EXECUTION_STARTED    hash
  PLAN_EXECUTION_FINISHED   hash

Example:

AUDIT PLAN_CREATED hash=abc123 AUDIT PLAN_APPROVED hash=abc123 AUDIT
PLAN_EXECUTION_STARTED hash=abc123 AUDIT PLAN_EXECUTION_FINISHED
hash=abc123

------------------------------------------------------------------------

# Required Tests

## Positive

submit → approve → execute

Verify: - steps run - audit logged

------------------------------------------------------------------------

## Deny: execution without approval

submit → execute

Expected:

PLAN_EXECUTION_DENIED

------------------------------------------------------------------------

## Deny: invalid schema

Submit malformed plan.

Expected:

validation error

------------------------------------------------------------------------

## Deny: raw tool call

Attempt:

git.run status

Expected:

DENIED: use PLAN

------------------------------------------------------------------------

# Sprint D Completion Criteria

Sprint D is complete when:

-   PLAN schema deterministic
-   plan hash generation implemented
-   plan approval required
-   all execution flows through execute_step()
-   raw execution paths denied
-   plan lifecycle events audited

------------------------------------------------------------------------

# Next Sprint (E Preview)

Sprint E will introduce:

Plan → Execute → Test → Diff → Summarize

plus transaction boundaries and automatic test runs.

Sprint D must enforce approval gating first.
