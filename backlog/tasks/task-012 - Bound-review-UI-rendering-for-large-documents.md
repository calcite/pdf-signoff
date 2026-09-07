---
id: TASK-012
title: Bound review UI rendering for large documents
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:26'
updated_date: '2026-09-07 17:00'
labels:
  - code-review
dependencies: []
references:
  - frontend/src/components/PdfDocument.vue
  - frontend/src/components/PdfPage.vue
  - frontend/src/placement.ts
modified_files:
  - frontend/src/components/PdfDocument.vue
  - frontend/src/components/PdfPage.vue
  - frontend/src/components/PdfPage.test.ts
  - frontend/src/App.test.ts
priority: low
type: enhancement
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`PdfDocument.vue` renders `v-for="page in pageCount"`, and each `PdfPage` calls `getPage` on mount and rasterises to a canvas at up to twice the device pixel ratio. Every page of the document is decoded and rasterised at once, with no virtualisation and no ceiling on page count.

For the short forms the specification targets this is fine and arguably preferable. It becomes a problem at scale: a few hundred pages allocates a few hundred full-resolution canvases during mount, and there is currently nothing that warns, degrades, or refuses.

Note the interaction with the save gate. `isPlacementStateValid` needs a rendered page size for every placement page, so any lazy-rendering scheme must still supply sizes for pages that were never rasterised, or Save will silently stop working.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Documents with many pages no longer rasterise every page during mount
- [x] #2 Page sizes remain available for every placement page so the save gate keeps working
- [x] #3 Scrolling to a page still renders it at full quality
- [x] #4 A frontend test covers placement validity for a page that has not been rasterised
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Load each page at scale 1 in PdfDocument to emit complete page-size metadata without rasterising canvases.
2. Pass measured dimensions to PdfPage and use IntersectionObserver to load, rasterise, and retain canvases only while pages are near the viewport.
3. Add regression coverage that page metadata enables validation and saving for a placement whose page is not rasterised.
4. Run frontend tests, type checking, and production build.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation: PdfPage currently calls getPage, emits its size, and schedules a high-DPI canvas render on every mount. App blocks Save until its page-size map contains every page, so measurement must be independent of viewport rendering.

Verified: npm test passed all 22 frontend tests, including intersection-driven rasterisation and Save for a measured, non-rasterised placement page; npm run typecheck, npm run build, and git diff --check also passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Measured all page viewports in PdfDocument before mounting page components, so the Save gate receives dimensions without canvas rasterisation. PdfPage now uses IntersectionObserver with a 600px margin to rasterise nearby pages at the existing high-DPI quality and clears canvases/PDF page resources after they leave the viewport. Verified with npm test (22 passing), npm run typecheck, npm run build, and git diff --check. No known limitations, follow-up tasks, or ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
