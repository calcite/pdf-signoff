---
id: TASK-001.05
title: Convert normalized placements to PDF geometry
status: To Do
assignee: []
created_date: '2026-09-04 18:03'
labels: []
dependencies:
  - TASK-001.03
  - TASK-001.04
references:
  - docs/pdf-sign-implementation-spec.md#13-coordinate-conversion-backend
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Browser placements are expressed against the displayed, rotated CropBox rather than raw PDF coordinates. A single authoritative conversion is needed to prevent UI and stamping paths from disagreeing on where a signature belongs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A single backend conversion maps a normalized displayed-page placement to the correct PyMuPDF rectangle
- [ ] #2 Conversion respects CropBox versus MediaBox, non-zero box origins, and rotations 0, 90, 180, and 270
- [ ] #3 Portrait, landscape, non-A4, and CropBox-smaller-than-MediaBox pages produce the expected physical rectangle
- [ ] #4 Frontend-facing displayed dimensions use the same page definition as backend conversion
- [ ] #5 Synthetic-PDF tests assert expected or round-trip geometry for every specified rotation and page-box case
<!-- AC:END -->
