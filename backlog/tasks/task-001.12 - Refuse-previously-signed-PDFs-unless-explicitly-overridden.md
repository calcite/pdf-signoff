---
id: TASK-001.12
title: Refuse previously signed PDFs unless explicitly overridden
status: To Do
assignee: []
created_date: '2026-09-04 18:04'
labels: []
dependencies:
  - TASK-001.07
references:
  - docs/pdf-sign-implementation-spec.md#16-existing-digital-signatures-on-input
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Stamping or rewriting a cryptographically signed input can invalidate prior signatures. Detect this condition before either automatic processing or browser launch and require an expert override so normal workflows cannot silently damage an existing signature.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Input inspection detects existing cryptographic PDF signatures before opening the review UI or modifying any output
- [ ] #2 A signed input is refused by default with an error explaining that stamping may invalidate prior signatures
- [ ] #3 `--allow-signed-input` permits processing and emits a strong warning only to stderr
- [ ] #4 Override output and messaging make no claim that any previous signature remains valid
- [ ] #5 Tests use a digitally signed fixture to verify default refusal, no partial output or stdout profile, and successful override with warning in supported signing modes
<!-- AC:END -->
