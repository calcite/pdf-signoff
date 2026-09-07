---
id: TASK-006
title: Explain why Save is disabled for preloaded placements
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:25'
updated_date: '2026-09-07 09:32'
labels:
  - code-review
dependencies: []
references:
  - frontend/src/placement.ts
  - frontend/src/App.vue
modified_files:
  - frontend/src/placement.ts
  - frontend/src/App.vue
  - frontend/src/App.test.ts
priority: medium
type: bug
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`isPlacementStateValid` requires every placement to sit within 5 percent of the current signature PNG aspect ratio, and it applies that rule to placements preloaded from `--coords` exactly as it does to freshly drawn ones. `initializePlacements` copies the stored width and height verbatim without re-deriving the height from the current image.

Reviewing an existing profile with a signature PNG of a different shape therefore produces a review session whose Save button is permanently disabled. `App.vue` surfaces no reason: `canSave` is a bare boolean and the status line shows nothing. The user sees a loaded document, visible signatures, and a dead control.

Either re-derive preloaded heights from the current PNG on load, or keep the strict check and tell the user which placements are inconsistent and what to do about them.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Loading a profile whose placements do not match the current PNG aspect either yields editable, correctly shaped placements or an explicit on-screen explanation
- [x] #2 The explanation names the affected pages and the action that clears it
- [x] #3 Save is never disabled without a visible reason
- [x] #4 A frontend test covers a preloaded profile whose aspect ratio does not match the session signature
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a placement-validation reason API that identifies invalid placement pages, including aspect-ratio mismatches.
2. Surface the active Save-disabled reason in the review toolbar, with a corrective action for mismatched preloaded signatures.
3. Add a regression test for an aspect-mismatched preloaded placement, then run the frontend test suite and typecheck.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation: preloaded placements remain editable; resizing one recalculates its height using the current PNG aspect. Preserve strict validation and explain the required resize or removal rather than silently altering stored geometry.

Implemented aspectMismatchedPlacementPages and toolbar Save-disabled guidance. The message identifies affected pages and instructs users to resize or remove mismatched signatures; generic loading, empty-state, and invalid-placement reasons are also shown. Verified with npm test (17 tests) and npm run typecheck in frontend/.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-07 09:32
---
Ready for human review. All acceptance criteria verified by frontend DOM tests and typecheck.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Changed the review toolbar to explain every Save-disabled state. Aspect-mismatched preloaded signatures now name their affected pages and instruct users to resize or remove them; resizing preserves the current PNG aspect and re-enables Save. Added App.vue regression coverage for the mismatch and empty-placement disabled states. Verified with npm test (17 passing tests) and npm run typecheck in frontend/. Known limitations: no browser end-to-end run was needed because the behavior is covered by DOM tests. Follow-up tasks: none. ADRs: none.
<!-- SECTION:FINAL_SUMMARY:END -->
