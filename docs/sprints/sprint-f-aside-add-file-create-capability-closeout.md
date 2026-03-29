# sprint-f-aside-add-file-create-capability — closeout

## summary

this slice introduced a **typed file mutation model**, replacing the implicit “patch-only” assumption with two explicit, constrained operations:

- `PATCH_APPLY` → modify existing files only  
- `FILE_CREATE` → create new files only  

no expansion of privilege surface. no relaxation of invariants.

---

## problem

previous state:

- all file mutation routed through `PATCH_APPLY`
- ambiguous behavior for missing files
- implicit assumptions about creation not enforced
- execution summary conflated create vs modify

this created:
- unclear safety boundaries
- inconsistent behavior across fs, validator, and docs
- misleading system-state reporting

---

## solution

introduced **separation of concerns at the mutation level**:

### 1. new tool surface

- added `FILE_CREATE` as first-class plan tool
- capability: `file.create`
- action: `FS_CREATE_FILE`

---

### 2. fs layer (fail-closed)

- atomic create (`"x"` mode)
- fails if:
  - file exists
  - parent missing
  - content > 64KB
- no mkdir
- no overwrite

---

### 3. gateway enforcement

- create routed through ToolGateway (no bypass)
- token required (exact-path scoped)
- policy enforced before fs
- denial paths audited
- no reuse of patch logic

---

### 4. policy alignment

- added `FS_CREATE_FILE` to allowlist
- enforced workspace boundary dynamically
- reused existing deny-by-default flow

---

### 5. execution semantics

summary now distinguishes:

created_paths   → FILE_CREATE only  
modified_paths  → PATCH_APPLY only  
changed_paths   → union (compatibility)

no more semantic ambiguity.

---

### 6. validator

- strict args:
  - `path` (required)
  - `content` (required)
- rejects:
  - `argv`
  - missing fields
  - wrong capability

---

### 7. test coverage

added coverage for:

- validator acceptance/rejection
- token enforcement
- policy boundary
- fs failure modes
- execution summary correctness

full suite:
58 passed

---

### 8. docs alignment

updated active docs to reflect:

PATCH_APPLY = existing-file only  
FILE_CREATE = new-file only  

left sprint-e docs unchanged (historical)

---

## invariants preserved

- ToolGateway remains choke point  
- deny-by-default policy  
- workspace boundary enforced  
- exact-path token scope  
- append-only audit  
- no implicit create via patch  
- no overwrite via create  
- no new execution surface (no shell/network expansion)  

---

## invariants added (explicit)

PATCH_APPLY:
- requires existing file
- cannot create files
- cannot create parent directories

FILE_CREATE:
- fails if file exists
- fails if parent missing
- atomic create only

---

## non-goals

not introduced:

- directory creation
- bulk writes
- partial writes
- overwrite semantics
- implicit mutation conversion

---

## outcome

the system now supports **deterministic, typed file mutation**:

- creation and modification are explicitly separated
- safety properties are preserved and clarified
- execution state reflects real behavior
- future extensions can build on typed operations without ambiguity

---

## forward considerations

possible future slices:

- directory creation (`DIR_CREATE`) with same constraints
- explicit overwrite tool (separate, not implicit)
- batch operations (still token + scope constrained)

---

## final state

mutation model: typed  
safety model: unchanged (strict)  
behavior: deterministic  
docs: aligned  
tests: passing
