---
id: TASK-001.07
title: Deliver headless L0 automatic signing
status: To Do
assignee: []
created_date: '2026-09-04 18:03'
labels: []
dependencies:
  - TASK-001.02
  - TASK-001.05
  - TASK-001.06
references:
  - docs/pdf-sign-implementation-spec.md#14-l0-implementation
  - docs/pdf-sign-implementation-spec.md#20-3-auto-mode
  - docs/pdf-sign-implementation-spec.md#22-tests
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Milestone 1 needs an end-to-end unattended path that applies validated profile placements through the shared backend pipeline. This is the first usable product slice and establishes the stdout/stderr process contract consumed by external agents.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Explicit `--auto` with a matching non-empty profile embeds the PNG at every placement and writes the resolved output PDF
- [ ] #2 PNG transparency is preserved, multiple placements and pages are supported, and clearly inconsistent physical rectangle aspect ratios are rejected rather than distorted
- [ ] #3 L0 output contains visual image placements without adding a cryptographic signature or proprietary Adobe Fill & Sign metadata
- [ ] #4 A successful command emits exactly one final profile JSON document on stdout, sends status and logs only to stderr, and exits zero
- [ ] #5 A failed command emits no profile JSON, exits non-zero, and leaves neither a partial output nor a modified input
- [ ] #6 Integration tests reopen and render synthetic outputs to verify expected signature regions, transparency, multiple pages, and unchanged input hashes; CLI tests enforce stdout, stderr, and exit-code behavior
<!-- AC:END -->
