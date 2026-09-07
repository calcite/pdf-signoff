---
id: TASK-001.03
title: Model and validate placement profiles
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:02'
updated_date: '2026-09-07 07:11'
labels: []
dependencies:
  - TASK-001.01
references:
  - docs/pdf-sign-implementation-spec.md#8-placement-profile-json
  - docs/pdf-sign-implementation-spec.md#18-suggested-internal-python-model
modified_files:
  - pdf_signoff/profile.py
  - tests/test_profile.py
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
- [x] #1 Pydantic models load and serialize version 1 profiles with the specified required and optional fields and 1-based page numbers
- [x] #2 Each placement is rejected unless its normalized rectangle is positive, in range, and fully contained by its referenced page
- [x] #3 Unknown versions are rejected, and auto mode rejects profiles with zero placements
- [x] #4 Final profiles include the current source SHA-256, displayed page metadata, rotations, and final placements while preserving input `required_text` conditions
- [x] #5 The same placement validation can be used by CLI profile loading and browser save requests
- [x] #6 Tests cover valid profiles, unknown versions, invalid pages and rectangles, zero placements, optional metadata, and required-text preservation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Implement strict version-1 Pydantic models in `pdf_signoff/profile.py` for normalized placements, page metadata, optional required-text/source metadata, and cross-field page-bound validation.
2. Add reusable placement-list validation, JSON file loading with auto-mode non-empty enforcement, deterministic JSON serialization, and final-profile construction from supplied source hash/page metadata/placements while preserving input required-text conditions.
3. Add focused profile tests for valid round trips, optional metadata, all invalid page/rectangle/version/empty cases, browser-oriented shared validation, and final-profile required-text behavior.
4. Run focused and full coverage tests, Ruff format/lint, and mypy; then record evidence and final task metadata while leaving the task In Progress.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation: `pdf_signoff/profile.py` is a one-line boundary with no implementation or tests. The v1 schema and normalized bounds are specified in sections 8 and 18; document inspection/matching belongs to TASK-001.04 and geometry/stamping to later tasks. The existing project uses Python 3.13, Pydantic v2, pytest with a 100% coverage threshold, Ruff, and mypy. This task will validate only schema-intrinsic page/rectangle rules and construct final profiles from metadata supplied by later inspection code.

Implementation result: added extra-field-forbidding Pydantic v2 models for placements, displayed page metadata, required-text conditions, source metadata, match specifications, and version-1 profiles. Cross-model validation constrains all page references to `page_count`; normalized rectangle validation is centralized in `validate_placements`, which accepts raw browser-style payloads and is also called during profile validation. `load_profile` applies context-sensitive auto-mode non-empty validation, `serialize_profile` omits absent optional metadata, and `build_final_profile` refreshes supplied source/page/placement metadata while retaining input `required_text`.

Verification evidence: `uv run pytest --cov=pdf_signoff.profile --cov-report=term-missing tests/test_profile.py` passed 29 tests with 100% focused coverage; `uv run pytest --cov=pdf_signoff --cov-report=term-missing tests/` passed all 72 tests with 100% project coverage; `uv run ruff format --check .`, `uv run ruff check .`, and `uv run mypy pdf_signoff` all passed. Modified files: `pdf_signoff/profile.py`, `tests/test_profile.py`. PDF inspection/matching, geometry, and stamping remain intentionally outside this task.
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
Implemented the canonical version-1 Pydantic placement/profile boundary, including normalized rectangle and page-reference validation, unknown-field/version rejection, reusable raw placement validation, JSON loading/serialization, auto-mode non-empty enforcement, and final-profile construction that refreshes current supplied source/page metadata while preserving input `required_text`.

Important choice: schema-intrinsic validation lives in `profile.py`; final-profile construction consumes already-inspected page metadata so TASK-001.04 retains PDF inspection and document matching, and later tasks retain geometry/stamping.

Verification: 29 focused tests passed at 100% `profile.py` coverage; all 72 project tests passed at 100% coverage; full Ruff format/lint and mypy passed. Known limitations are the intentional task boundary only. Follow-up work remains in existing TASK-001.04 and later subtasks. No blockers, no new follow-up tasks, and no ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
