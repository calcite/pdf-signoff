---
id: TASK-001.04
title: Inspect inputs and match profiles to PDFs
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:02'
updated_date: '2026-09-07 07:11'
labels: []
dependencies:
  - TASK-001.03
references:
  - docs/pdf-sign-implementation-spec.md#9-profiledocument-matching
  - docs/pdf-sign-implementation-spec.md#14-3-signature-png
  - docs/pdf-sign-implementation-spec.md#17-unsupportedproblematic-inputs
modified_files:
  - pdf_signoff/inspection.py
  - tests/test_inspection.py
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Coordinates are safe to reuse only when the current PDF has the expected displayed geometry and optional textual anchors, and signing must reject unsupported files before opening a browser or creating output. Centralize input inspection and conservative profile/document matching. Listed page dimensions use an inclusive absolute tolerance of 1 PDF point.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Readable, unencrypted, non-empty PDFs and decodable PNG signature assets pass startup inspection, while malformed, encrypted, zero-page, or non-PNG inputs fail clearly
- [x] #2 Displayed CropBox dimensions and normalized rotations are reported consistently for every page
- [x] #3 Profile matching requires equal page count and matching listed page size within the defined tolerance and rotation
- [x] #4 Optional required text is matched on its requested page or document-wide after whitespace normalization, and all conditions must pass
- [x] #5 `created_from.sha256` remains informational and does not cause an otherwise reusable profile to fail matching
- [x] #6 Tests cover all supported and rejected input classes plus page-count, size, rotation, required-text, and whitespace matching outcomes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Implement immutable inspection result types and clear domain errors in `pdf_signoff/inspection.py`; inspect PDFs with PyMuPDF for true PDF type, encryption, repair state, nonzero pages, displayed CropBox dimensions/normalized rotations, extractable text, and SHA-256; inspect signature assets by PNG magic plus full PyMuPDF decode.
2. Implement profile/document matching with exact page count and rotation, a 1-point inclusive displayed-size tolerance using finite-safe comparisons, and whitespace-normalized page-scoped or document-wide required-text substring checks; deliberately ignore `created_from.sha256`.
3. Add focused generated-fixture tests covering valid PDF/PNG inspection, malformed/repaired/encrypted/zero-page/non-PDF and non-PNG/undecodable inputs, all rotations/CropBoxes, matching successes and each page-count/size/rotation/text failure, whitespace normalization, all-condition behavior, and informational hashes.
4. Run focused and full pytest with project coverage, Ruff format/lint, mypy, and fixture checks; synchronize evidence and final task metadata while leaving the task In Progress.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation: inspection.py is an untouched one-line boundary; profile.py supplies PageMatch and PlacementProfile from TASK-001.03. Runtime versions are PyMuPDF 1.28.2 and Pydantic 2.13.5. PyMuPDF documents Page.rect as the displayed page rectangle reflecting rotation and Page.cropbox as unrotated; Document.needs_pass identifies password-required input and Document.is_repaired identifies open-time repair. PyMuPDF image_profile currently raises a TypeError on valid PNG bytes in this environment, so PNG validation will use the fixed PNG signature plus Pixmap full decode rather than that helper. Pydantic permits NaN/Infinity by default, so profile size comparison must use math.isclose (non-finite values cannot bypass it) rather than a greater-than-only delta check. Scope explicitly excludes geometry conversion, stamping, and existing-digital-signature policy.

Implementation checkpoint: pdf_signoff/inspection.py now defines conservative PDF/PNG inspection results and errors, extracts SHA-256/page text/displayed Page.rect metadata, normalizes quarter-turn rotations, and rejects non-PDF, encrypted, repaired, zero-page, unreadable, invalid-geometry, non-PNG, and undecodable image inputs. validate_profile_match enforces page count, listed page sizes within an inclusive 1-point absolute tolerance, rotations, and all normalized-whitespace text conditions at page or document scope; created_from is never consulted. tests/test_inspection.py uses generated PyMuPDF and minimal-PDF fixtures and targeted failure doubles. Focused verification currently passes 24 tests at 100% inspection coverage; full verification passes 96 tests at 100% project coverage, with full Ruff format/lint and mypy clean.

Final verification commands: `uv run pytest --cov=pdf_signoff.inspection --cov-report=term-missing tests/test_inspection.py` passed 24 tests at 100%; `uv run pytest --cov=pdf_signoff --cov-report=term-missing tests/` passed 96 tests at 100% project coverage; `uv run ruff format --check .` reported 15 files formatted; `uv run ruff check .` passed; `uv run mypy pdf_signoff` passed for 10 source files. Generated fixture checks exercise real PyMuPDF CropBox/rotation/text extraction, AES-256 password protection, repair detection, a structurally valid zero-page PDF, and PNG/JPEG decoding.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-04 19:27
---
**Human:** Implement TASK-001.04 only; earlier subtasks remain In Progress pending acceptance, and do not include geometry conversion, stamping, or existing-digital-signature policy.
---

author: Human
created: 2026-09-07 07:11
---
The human reviewed the implementation and confirmed it works; accepted for completion.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented conservative PDF and PNG inspection plus reusable profile/document matching. PDF inspection now rejects unreadable, non-PDF, encrypted, repaired/malformed, zero-page, and invalid-geometry inputs while reporting SHA-256, extracted text, and displayed CropBox dimensions/normalized rotations. PNG inspection requires PNG bytes to decode fully and reports dimensions/alpha availability. Matching requires page count, each listed size within an inclusive 1-point tolerance, rotation, and every whitespace-normalized page/document text condition; `created_from.sha256` remains informational.

Important choices: `Page.rect` supplies displayed CropBox geometry; recoverable repair is rejected conservatively; PNG magic plus `Pixmap` is used because PyMuPDF 1.28.2 `image_profile` raises on valid bytes in this environment; finite-safe `math.isclose` rejects non-finite profile dimensions.

Verification: 24 focused tests passed with 100% inspection coverage; all 96 tests passed with 100% project coverage; full Ruff format/lint and mypy passed. Generated fixtures cover all requested input and matching classes. Known limitation: required-text matching uses PyMuPDF-extractable text and does not add OCR. Geometry conversion, stamping, and existing-signature policy remain in later tasks by design. No blockers, new follow-up tasks, or ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
