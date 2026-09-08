---
id: TASK-014
title: Show reviewed PDF filename
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-08 07:41'
updated_date: '2026-09-08 08:42'
labels: []
dependencies: []
priority: medium
type: feature
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The local review interface does not currently identify the document being reviewed, making simultaneous browser sessions difficult to distinguish. Show the input document basename without exposing filesystem paths in both the toolbar and browser tab.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The authenticated session metadata supplies the reviewed input document basename and never its directory path.
- [x] #2 The toolbar visibly identifies the reviewed file while retaining usable document actions on desktop and mobile widths.
- [x] #3 After session metadata loads, the browser tab title is exactly <filename> - PDF signoff.
- [x] #4 Backend, frontend unit, and end-to-end tests cover filename display and path privacy.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a basename-only documentName field to the authenticated session metadata and retain the path-privacy contract.
2. Consume documentName in the Vue review app, render it in the responsive toolbar, and set the tab title to <filename> - PDF signoff after metadata loads.
3. Cover the backend contract, frontend rendering/title behavior, and browser flow; rebuild the packaged frontend assets.
4. Run the focused Python and frontend verification commands and move the task to review.

5. Increase the visual gap between the filename and status in the toolbar, then rebuild and verify the browser layout.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Investigation confirmed that ReviewSession retains the selected Path but SessionMetadata currently exposes only page and placement facts. The top bar is frontend/src/App.vue and document.title is not set. Use Path.name rather than a document response header so the frontend receives a deterministic, path-free value.

Verification passed: uv run pytest --cov=pdf_signoff tests/ (230 passed, 100% coverage); npm run typecheck; npm test (23 passed); npm run build; npm run test:e2e (2 passed, including a 375px mobile viewport).

Follow-up adjustment: increased the status margin below the filename to 0.3rem on desktop and 0.35rem on mobile. Verified with npm run build and npm run test:e2e (2 passed).
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-08 08:41
---
Human: Requested slightly more spacing between the filename and document status in the top bar.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented basename-only document metadata and rendered it in the responsive review toolbar and browser tab as <filename> - PDF signoff.

The backend uses Path.name, preserving directory-path privacy. The toolbar ellipsizes long names, reflows its filename/details above the actions on mobile, and now provides a slightly larger gap between the filename and status. Rebuilt pdf_signoff/web_dist.

Verified initially with the full Python coverage suite, frontend type check and unit tests, production build, and Playwright E2E at desktop and 375px mobile widths. The spacing follow-up was verified with npm run build and npm run test:e2e (2 passed).

Known limitations: None.
Follow-up tasks: None.
ADRs: None.
<!-- SECTION:FINAL_SUMMARY:END -->
