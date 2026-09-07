---
id: TASK-003
title: Validate profile geometry for every page a placement targets
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:25'
updated_date: '2026-09-07 08:58'
labels:
  - code-review
dependencies: []
references:
  - pdf_signoff/inspection.py
  - pdf_signoff/profile.py
  - tests/test_profile.py
  - tests/test_cli.py
  - README.md
modified_files:
  - pdf_signoff/profile.py
  - tests/test_profile.py
  - tests/test_cli.py
  - README.md
priority: medium
type: bug
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Profile/document matching in `validate_profile_match` iterates only the entries the profile happens to list in `match.pages`. Nothing requires that list to cover all pages, to be free of duplicates, or to include the pages the placements actually reference.

Verified on the current tree with a two-page PDF (page 1 A4 portrait 595x842 pt, page 2 A4 landscape 842x595 pt): a profile declaring `page_count: 2`, listing geometry for page 1 only, and placing a signature on page 2 is accepted. Page 2 CropBox size and rotation are never compared. A profile listing page 1 twice is also accepted.

Profiles emitted by the tool always list every page, so this only bites hand-edited or truncated profiles. But the README promises that a profile is checked against the document before reuse, and rotation in particular changes how a normalized placement maps onto the page, so an unchecked page can put the signature in the wrong place on a document that superficially matches.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `match.pages` describes each page 1..page_count exactly once
- [x] #2 Duplicate page entries in `match.pages` are rejected with a clear message
- [x] #3 A profile placing a signature on a page whose geometry was never listed is rejected before any output is written
- [x] #4 Tests cover a truncated page list, a duplicated page entry, and a placement on an unlisted page
- [x] #5 README profile documentation states the coverage requirement
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Enforce unique, complete match.pages coverage for page numbers 1 through page_count in MatchSpec validation.
2. Add model tests for truncated and duplicate page metadata plus an automatic CLI regression for a placement targeting omitted metadata.
3. Document the match.pages coverage requirement and run focused and full project checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Investigation confirmed load_profile validates PlacementProfile before automatic or review workflows can write output. Tool-generated profiles already include every inspected page. The minimal fix is a MatchSpec invariant: reject duplicate metadata first, then report any missing page numbers; ordering remains unrestricted.

Implemented complete and unique MatchSpec page metadata validation. Validation evidence: `uv run pytest --cov=pdf_signoff --cov-report=term-missing` passed 222 tests with 100% coverage; `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy pdf_signoff` passed. `uv run mypy pdf_signoff tests` still reports five unrelated pre-existing test typing errors in test_config.py, test_inspection.py, and test_server.py.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-07 08:56
---
Implementation and verification are complete; ready for human review. The project has no configured Review status, so the task remains In Progress for human acceptance.
---

author: Human
created: 2026-09-07 08:58
---
Reviewed and checked; approved for closure.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Profiles now require exactly one `match.pages` metadata entry for every declared page. Duplicate and missing entries produce explicit validation errors before signing can write output. Added model regressions for truncated/duplicate lists, an automatic CLI no-artifact regression for an unlisted placement page, and README documentation. Verified all 222 tests at 100% coverage plus Ruff and source-package mypy.
<!-- SECTION:FINAL_SUMMARY:END -->
