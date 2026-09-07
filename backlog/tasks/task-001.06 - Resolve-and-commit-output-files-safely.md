---
id: TASK-001.06
title: Resolve and commit output files safely
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:03'
updated_date: '2026-09-07 07:11'
labels: []
dependencies:
  - TASK-001.02
references:
  - docs/pdf-sign-implementation-spec.md#6-output-path-resolution
  - >-
    docs/pdf-sign-implementation-spec.md#5-process-exit-and-stdoutstderr-behavior
modified_files:
  - pdf_signoff/output.py
  - pdf_signoff/cli.py
  - tests/test_output.py
  - tests/test_cli.py
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
- [x] #1 Output selection follows explicit `--output`, configured suffix, then `_signed`, preserving multi-dot base names
- [x] #2 Input and output resolving to the same file are rejected even when overwrite is enabled
- [x] #3 An existing destination is rejected unless `--overwrite` is explicit
- [x] #4 Writes use a temporary file in the destination directory and atomically commit only a fully successful result
- [x] #5 Failures and interruption remove temporary artifacts, leave existing destinations untouched, and never modify the input
- [x] #6 Tests cover default and configured suffixes, explicit output, multi-dot names, path equality, collisions, overwrite, atomic replacement, and failed-write cleanup
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Implement output-path errors and deterministic `resolve_output_path` precedence in `pdf_signoff/output.py`, rejecting resolved/same-file aliases and destination collisions conservatively.
2. Implement a reusable callback-based atomic writer that creates a same-directory temporary file, commits with no-clobber semantics or atomic replacement as requested, and cleans up on every `BaseException`.
3. Resolve the final output during existing CLI validation without invoking stamping or signing.
4. Add focused output and CLI tests for naming, configured/default/explicit precedence, aliases, collisions, race-safe overwrite semantics, atomic commit, writer/commit failures, interruption cleanup, and source preservation.
5. Run focused and full tests with coverage, Ruff format/lint, and mypy; then finalize the Backlog record while leaving it In Progress.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented `resolve_output_path` as the shared CLI/config/default naming boundary. It preserves the final extension for multi-dot names, compares non-strict resolved paths and existing-file identity to reject symlink and hard-link aliases, treats broken symlinks as collisions, and fails conservatively when paths cannot be resolved or compared. `write_output_atomically` accepts a reusable writer callback, creates its temporary file in the destination directory, publishes without overwrite via atomic hard-link creation (preventing check/commit races), and uses `os.replace` for requested overwrite; a `finally` removes temporary files after writer exceptions, `KeyboardInterrupt`, publication races, and replacement failures. CLI validation now returns the resolved output in `Invocation`; stamping and complete signing integration remain scoped to TASK-001.07. Verification: focused output/CLI suite 39 passed with 100% coverage; full suite 134 passed with 100% coverage; `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy pdf_signoff`, and `git diff --check` passed. No ADR was needed. Dependencies remain In Progress pending human acceptance as reported.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @human
created: 2026-09-04 19:38
---
Implement only this output-resolution and transactional-commit subtask; dependencies were reported implemented and verified but remain In Progress pending human acceptance. Do not add stamping or full signing integration beyond reusable interfaces.
---

author: Human
created: 2026-09-07 07:11
---
The human reviewed the implementation and confirmed it works; accepted for completion.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented deterministic explicit/config/default output resolution and reusable transactional output commits. Path validation rejects resolved symlink aliases, hard links, comparison failures, and unapproved existing or broken-symlink destinations. Writes use same-directory temporary files, race-safe no-clobber publication, atomic overwrite replacement, and `BaseException` cleanup while preserving input and prior destinations. Added focused naming, CLI, alias, collision, overwrite, race, atomicity, failure, and interruption tests. Verified 39 focused and 134 full tests at 100% coverage, Ruff format/lint, mypy, and diff whitespace. Known limitation/follow-up: this task intentionally does not stamp PDFs or wire the full signing workflow; TASK-001.07 consumes these interfaces. No ADRs or implementation blockers.
<!-- SECTION:FINAL_SUMMARY:END -->
