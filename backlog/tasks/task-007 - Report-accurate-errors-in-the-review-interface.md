---
id: TASK-007
title: Report accurate errors in the review interface
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:25'
updated_date: '2026-09-07 13:10'
labels:
  - code-review
dependencies: []
references:
  - frontend/src/App.vue
  - frontend/src/components/PdfPage.vue
modified_files:
  - frontend/src/App.vue
  - frontend/src/App.test.ts
  - frontend/src/components/PdfDocument.vue
  - pdf_signoff/web_dist/index.html
  - pdf_signoff/web_dist/assets/index-CI8FD2lt.js
  - pdf_signoff/web_dist/assets/index-DcgIssN2.js
priority: low
type: bug
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two problems with error reporting in `App.vue`.

`reportError` discards its argument and always sets "Unable to load the review session." It is wired to the `error` event from `PdfDocument` and `PdfPage`, so a mid-session canvas render failure or a page fetch failure reports a misleading load error.

The status line orders its branches `saved`, `saving`, `placeMode`, then `errorMessage`. Any error raised while place mode is active is rendered invisible by the earlier branch.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Load failures, per-page render failures, and save failures produce distinguishable messages
- [x] #2 An error is visible regardless of place mode or save state
- [x] #3 No message exposes an internal path, URL, or stack trace
- [x] #4 A frontend test covers a render error raised while place mode is active
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Route review-session, PDF-document, and PDF-page failures to source-specific safe status messages.
2. Render errors ahead of saved, saving, and placement status.
3. Extend the App integration test for a page render error while placement mode is active, then run frontend checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Investigation: App.vue uses one generic reportError handler for initial session fetches and PdfDocument error events; PdfDocument forwards both document-load and PdfPage failures without context. The existing save handler already uses a distinct safe message.

Implemented source-tagged PDF document/page error propagation and safe session, document, page-render, and save messages. Validation passed: npm test (20 tests) and npm run build (vue-tsc plus Vite production build). App tests exercise document-load, render-during-place-mode, render-during-save, post-save, and save-failure status behavior using internal-looking paths.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-07 13:00
---
Agent: Implementation and verification are complete and ready for human review. The task remains In Progress because this project has no Review status and only the human may accept completion.
---

author: Human
created: 2026-09-07 13:10
---
Human: Approved task 007 for completion.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Replaced the generic PDF error path with source-aware, user-safe document and page-render messages while retaining separate session-load and save-failure messages. Errors now take precedence over saved, saving, placement, and disabled-save status. Rebuilt the frontend distribution. Verified with npm test (20 tests) and npm run build; the added App coverage confirms safe render errors during placement and saving, document errors after save, and safe save failures. No follow-up tasks or ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
