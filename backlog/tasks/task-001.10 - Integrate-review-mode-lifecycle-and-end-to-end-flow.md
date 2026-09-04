---
id: TASK-001.10
title: Integrate review-mode lifecycle and end-to-end flow
status: To Do
assignee: []
created_date: '2026-09-04 18:04'
labels: []
dependencies:
  - TASK-001.09
references:
  - docs/pdf-sign-implementation-spec.md#10-7-save
  - docs/pdf-sign-implementation-spec.md#20-2-review-mode
  - docs/pdf-sign-implementation-spec.md#22-6-frontend-tests
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The default CLI workflow must coordinate browser launch, one-shot server lifetime, backend save completion, final profile emission, and interruption cleanup. Integrate the completed API and frontend into an installed command and prove that human edits, rather than suggested coordinates, become the final signed state.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Review mode starts the protected local server, opens the tokenized browser URL when configured, and preloads coordinates only after profile/document validation succeeds
- [ ] #2 A successful browser save completes output before responding, emits exactly one profile containing the edited final placements on CLI stdout, logs status only to stderr, shuts down after the response, and exits zero
- [ ] #3 Closing the browser without saving leaves the CLI waiting, while Ctrl+C cleanly stops the server, removes temporary files, emits no profile JSON, and uses the normal interrupted-process status
- [ ] #4 The Vite production build is packaged into the Python distribution so an installed review workflow requires no Node runtime
- [ ] #5 A Playwright test preloads, drags, resizes, removes, replaces, and saves a signature, then asserts the output and emitted edited profile
- [ ] #6 End-to-end coverage also verifies a no-coordinates session starts empty and no save dialog or browser download occurs
<!-- AC:END -->
