---
id: TASK-001.13
title: 'Complete release packaging, documentation, and verification'
status: To Do
assignee: []
created_date: '2026-09-04 18:04'
updated_date: '2026-09-04 18:38'
labels: []
dependencies:
  - TASK-001.10
  - TASK-001.11
  - TASK-001.12
references:
  - docs/pdf-sign-implementation-spec.md#23-implementation-milestones
  - docs/pdf-sign-implementation-spec.md#24-definition-of-done
  - docs/pdf-sign-implementation-spec.md#25-explicit-non-goals-for-the-mvp
parent_task_id: TASK-001
priority: medium
type: docs
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The completed subsystems must ship as one reproducible local utility with clear operational boundaries. Finish installation and usage documentation, verify built artifacts rather than only source checkouts, and run the cross-cutting test matrix that demonstrates the draft definition of done.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 README documentation covers installation, configuration, review, auto, output capture, overwrite, signed-input override, and L0 versus L1 semantics with executable examples
- [ ] #2 Documentation states localhost and credential assumptions, unsupported input classes, agent/workflow responsibility, and all explicit MVP non-goals without overstating legal identity assurance
- [ ] #3 A built wheel contains the production frontend and all required package data, and `pdf-signoff` review and auto smoke tests pass from an isolated installation without Node.js
- [ ] #4 The Python unit/integration suite, Vitest suite, and Playwright workflow pass together on Python 3.13 using locked dependencies
- [ ] #5 Release verification demonstrates all top-level definition-of-done behaviors, including stdout isolation, deterministic safe outputs, geometry edge cases, review edits, L1 integrity, signed-input protection, and loopback session security
<!-- AC:END -->
