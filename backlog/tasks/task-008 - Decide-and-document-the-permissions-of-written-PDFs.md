---
id: TASK-008
title: Decide and document the permissions of written PDFs
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:25'
updated_date: '2026-09-07 13:23'
labels:
  - code-review
dependencies: []
references:
  - pdf_signoff/output.py
priority: low
type: task
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`write_output_atomically` stages through `tempfile.mkstemp`, which creates the file 0600. Neither `os.replace` nor `os.link` changes the mode, so the published PDF keeps 0600 and ignores the process umask. Verified on the current tree: a file written through this path has mode 0o600 under the default umask, where a normally created file would be 0644.

Restrictive permissions on a signed document are defensible, and may well be the intent. But nothing in the code, the README, or the spec records the choice, so it currently reads as an accident of `mkstemp`. It is also a surprise when the output feeds a shared directory or a different service account, which is a realistic shape for the agent workflows this tool targets.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The intended permission model for published outputs is chosen and recorded
- [x] #2 The staging path applies that model explicitly rather than inheriting `mkstemp` defaults
- [x] #3 The behaviour is stated in the README where output commit is described
- [x] #4 A test asserts the resulting mode
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Publish completed PDFs with an explicit 0644 mode while retaining mkstemp's 0600 protection during staging.
2. Apply the mode immediately before atomic publication and add focused coverage for both no-clobber and overwrite commits.
3. Document the POSIX permission contract beside the README's output-commit description.
4. Run focused and project checks, then record verification evidence for review.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation: output.py creates staging files with tempfile.mkstemp, whose 0600 mode survives both os.link and os.replace. The reviewed expected default is 0644. The selected contract is explicit POSIX mode 0644 for published PDFs, enabling shared-directory/service-account workflows; staging remains 0600 until a completed file is committed.

Implementation and verification: write_output_atomically keeps the mkstemp path 0600 while stages run, then chmods the completed file to explicit 0644 before either os.link or os.replace publishes it. The focused output suite passed 25 tests. The full suite passed 227 tests with 100.00% coverage; Ruff lint/format, mypy, uv lock --check, and git diff --check passed. The full suite retains one pre-existing Starlette/AnyIO deprecation warning.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-07 13:20
---
Ready for human review; Done is the configured terminal status.
---

author: @human
created: 2026-09-07 13:23
---
Human accepted the implementation and requested task closure.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Set the published-PDF contract to POSIX 0644, retaining private 0600 staging until commit. Documented the contract in the README and added restrictive-umask coverage for both no-clobber and overwrite publication. Verified with 25 focused tests and 227 full tests at 100% coverage, plus Ruff, mypy, lock, and whitespace checks. No ADRs or follow-up tasks.
<!-- SECTION:FINAL_SUMMARY:END -->
