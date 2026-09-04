---
id: TASK-001.06
title: Resolve and commit output files safely
status: To Do
assignee: []
created_date: '2026-09-04 18:03'
labels: []
dependencies:
  - TASK-001.02
references:
  - docs/pdf-sign-implementation-spec.md#6-output-path-resolution
  - >-
    docs/pdf-sign-implementation-spec.md#5-process-exit-and-stdoutstderr-behavior
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Signing must never mutate its source, surprise-overwrite a result, or leave a partial PDF. Isolate deterministic naming and destination commit behavior so both automatic and browser workflows receive identical guarantees.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Output selection follows explicit `--output`, configured suffix, then `_signed`, preserving multi-dot base names
- [ ] #2 Input and output resolving to the same file are rejected even when overwrite is enabled
- [ ] #3 An existing destination is rejected unless `--overwrite` is explicit
- [ ] #4 Writes use a temporary file in the destination directory and atomically commit only a fully successful result
- [ ] #5 Failures and interruption remove temporary artifacts, leave existing destinations untouched, and never modify the input
- [ ] #6 Tests cover default and configured suffixes, explicit output, multi-dot names, path equality, collisions, overwrite, atomic replacement, and failed-write cleanup
<!-- AC:END -->
