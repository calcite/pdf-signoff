---
id: TASK-001.05
title: Convert normalized placements to PDF geometry
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:03'
updated_date: '2026-09-07 07:11'
labels: []
dependencies:
  - TASK-001.03
  - TASK-001.04
references:
  - docs/pdf-sign-implementation-spec.md#13-coordinate-conversion-backend
modified_files:
  - pdf_signoff/geometry.py
  - pdf_signoff/inspection.py
  - tests/test_geometry.py
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
- [x] #1 A single backend conversion maps a normalized displayed-page placement to the correct PyMuPDF rectangle
- [x] #2 Conversion respects CropBox versus MediaBox, non-zero box origins, and rotations 0, 90, 180, and 270
- [x] #3 Portrait, landscape, non-A4, and CropBox-smaller-than-MediaBox pages produce the expected physical rectangle
- [x] #4 Frontend-facing displayed dimensions use the same page definition as backend conversion
- [x] #5 Synthetic-PDF tests assert expected or round-trip geometry for every specified rotation and page-box case
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a shared displayed-page geometry helper based on PyMuPDF Page.rect and make PDF inspection consume it.
2. Implement placement_to_pdf_rect as the sole normalized displayed-CropBox conversion: scale into rotated displayed coordinates, then apply Page.derotation_matrix for PyMuPDF page-operation coordinates.
3. Add synthetic-PDF tests with explicit expected rectangles and transform round trips for rotations 0/90/180/270, plus portrait, landscape, non-A4, non-zero MediaBox/CropBox origins, and CropBox-smaller-than-MediaBox cases.
4. Run focused and full tests with coverage, Ruff format/lint, and mypy; synchronize task evidence without implementing stamping.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Investigation (PyMuPDF 1.28.2): Page.rect / Page.bound reflects rotation and the visible CropBox, with displayed dimensions swapped for 90/270. PyMuPDF documents that page modification methods accept unrotated coordinates; Page.derotation_matrix converts displayed coordinates to that space. Synthetic probing confirms Page.rect starts at (0, 0), its full rectangle derotates to (0, 0, CropBox.width, CropBox.height), and non-zero CropBox/MediaBox origins are already absorbed by PyMuPDF. Adding cropbox_position would therefore misplace content. Frontend-facing dimensions should come from the same Page.rect helper used by conversion and inspection.

Implementation evidence:
- pdf_signoff.geometry now provides displayed_cropbox_rect() and the sole normalized conversion placement_to_pdf_rect(). The conversion scales against the rotated Page.rect and applies Page.derotation_matrix.
- pdf_signoff.inspection uses displayed_cropbox_rect(), so emitted/frontend-facing PageMatch dimensions and conversion share one displayed-page definition.
- tests/test_geometry.py creates and reopens synthetic PDFs. Explicit expected rectangles and rotation-matrix round trips cover 0/90/180/270 with non-zero MediaBox and CropBox origins; separate cases cover A4 portrait, Letter landscape, non-A4 wide, and CropBox-smaller-than-MediaBox geometry.
Verification (Python 3.13.15, PyMuPDF 1.28.2): uv run pytest tests/test_geometry.py --cov=pdf_signoff.geometry --cov-report=term-missing --cov-fail-under=100 => 13 passed, geometry 100%; uv run pytest --cov=pdf_signoff --cov-report=term-missing tests/ => 109 passed, project 100%; uv run ruff format --check . => 16 files already formatted; uv run ruff check . => passed; uv run mypy pdf_signoff => passed (10 source files); uv run mypy tests/test_geometry.py => passed. An additional non-canonical uv run mypy pdf_signoff tests reports four pre-existing errors confined to tests/test_inspection.py and tests/test_config.py; no TASK-001.05 file errors remain.
Coordinate caveat: the returned Rect is in PyMuPDF unrotated, top-left, CropBox-local page-operation coordinates, not raw PDF bottom-left coordinates. Page.derotation_matrix already absorbs CropBox/MediaBox origins, so cropbox_position must not be added. Visual image orientation/aspect handling remains stamping work and was intentionally not implemented.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Human
created: 2026-09-07 07:11
---
The human reviewed the implementation and confirmed it works; accepted for completion.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the authoritative normalized displayed-CropBox conversion in pdf_signoff/geometry.py: normalized browser coordinates are scaled using the rotated Page.rect definition and transformed with Page.derotation_matrix into coordinates accepted by PyMuPDF page APIs. Routed PDF inspection metadata through the same displayed_cropbox_rect() helper and added 13 synthetic-PDF geometry tests covering all four rotations, explicit transform round trips, portrait/landscape/non-A4 dimensions, smaller CropBoxes, and non-zero MediaBox/CropBox origins.

Verification: focused geometry tests passed 13/13 at 100% geometry coverage; full tests passed 109/109 at 100% project coverage; Ruff format check and lint passed; canonical source mypy and the new geometry test mypy passed.

Known limitations: output coordinates are deliberately PyMuPDF CropBox-local unrotated coordinates rather than raw PDF coordinates. Stamping and image-orientation/aspect behavior are outside this subtask and unchanged. Follow-up tasks: none created; stamping remains in its existing Backlog scope. ADRs: none required.
<!-- SECTION:FINAL_SUMMARY:END -->
