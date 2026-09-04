---
id: TASK-001.03
title: Model and validate placement profiles
status: To Do
assignee: []
created_date: '2026-09-04 18:02'
labels: []
dependencies:
  - TASK-001.01
references:
  - docs/pdf-sign-implementation-spec.md#8-placement-profile-json
  - docs/pdf-sign-implementation-spec.md#18-suggested-internal-python-model
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Automatic reuse and browser review must exchange one versioned, normalized placement model. Define the canonical profile and final-profile construction rules so hand-edited or future-incompatible data is rejected rather than guessed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Pydantic models load and serialize version 1 profiles with the specified required and optional fields and 1-based page numbers
- [ ] #2 Each placement is rejected unless its normalized rectangle is positive, in range, and fully contained by its referenced page
- [ ] #3 Unknown versions are rejected, and auto mode rejects profiles with zero placements
- [ ] #4 Final profiles include the current source SHA-256, displayed page metadata, rotations, and final placements while preserving input `required_text` conditions
- [ ] #5 The same placement validation can be used by CLI profile loading and browser save requests
- [ ] #6 Tests cover valid profiles, unknown versions, invalid pages and rectangles, zero placements, optional metadata, and required-text preservation
<!-- AC:END -->
