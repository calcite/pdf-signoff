---
id: TASK-001.04
title: Inspect inputs and match profiles to PDFs
status: To Do
assignee: []
created_date: '2026-09-04 18:02'
labels: []
dependencies:
  - TASK-001.03
references:
  - docs/pdf-sign-implementation-spec.md#9-profiledocument-matching
  - docs/pdf-sign-implementation-spec.md#14-3-signature-png
  - docs/pdf-sign-implementation-spec.md#17-unsupportedproblematic-inputs
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Coordinates are safe to reuse only when the current PDF has the expected displayed geometry and optional textual anchors, and signing must reject unsupported files before opening a browser or creating output. Centralize input inspection and conservative profile/document matching.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Readable, unencrypted, non-empty PDFs and decodable PNG signature assets pass startup inspection, while malformed, encrypted, zero-page, or non-PNG inputs fail clearly
- [ ] #2 Displayed CropBox dimensions and normalized rotations are reported consistently for every page
- [ ] #3 Profile matching requires equal page count and matching listed page size within the defined tolerance and rotation
- [ ] #4 Optional required text is matched on its requested page or document-wide after whitespace normalization, and all conditions must pass
- [ ] #5 `created_from.sha256` remains informational and does not cause an otherwise reusable profile to fail matching
- [ ] #6 Tests cover all supported and rejected input classes plus page-count, size, rotation, required-text, and whitespace matching outcomes
<!-- AC:END -->
