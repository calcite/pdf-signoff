---
id: TASK-009
title: Expose review session resources through public accessors
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:25'
updated_date: '2026-09-07 13:26'
labels:
  - code-review
dependencies: []
references:
  - pdf_signoff/server.py
modified_files:
  - pdf_signoff/server.py
priority: low
type: chore
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The `/api/document` and `/api/signature` route handlers in `create_review_app` read `session._input_pdf` and `session._signature_png` directly. `ReviewSession` otherwise keeps a deliberate private boundary and offers `token`, `is_active`, and `metadata` as its public surface, so these two reads are the only place the boundary is crossed.

This is a small change, but the private names are exactly the state that decides which files the server will hand to a browser, so it is worth keeping inside the class contract.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The route handlers obtain the PDF and PNG paths through public read-only members of `ReviewSession`
- [x] #2 No underscore-prefixed attribute of `ReviewSession` is referenced outside the class
- [x] #3 Existing server tests continue to pass unchanged
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add read-only `ReviewSession` accessors for the fixed document and signature paths.
2. Use those accessors in the document and signature route handlers.
3. Run the existing server tests and verify no `ReviewSession` private resource attribute is read outside the class.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented read-only input_pdf and signature_png properties on ReviewSession; /api/document and /api/signature now use them. Validation passed: uv run pytest tests/test_server.py (38 passed) and a focused TestClient runtime check that substitutes each property and confirms its route serves the substituted file. Repository search found no external session._input_pdf or session._signature_png reads.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Exposed the session's selected PDF and signature paths through read-only public properties and updated both file routes to use them. Verified by the unchanged server suite (38 passed) and a focused property-substitution route check. No follow-up work or ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
