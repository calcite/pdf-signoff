---
id: TASK-001.09
title: Build the Vue PDF placement interface
status: In Progress
assignee:
  - '@opencode'
created_date: '2026-09-04 18:03'
updated_date: '2026-09-04 20:18'
labels: []
dependencies:
  - TASK-001.08
references:
  - docs/pdf-sign-implementation-spec.md#10-interactive-web-ui
modified_files:
  - .gitignore
  - frontend/index.html
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/tsconfig.json
  - frontend/vite.config.ts
  - frontend/src/env.d.ts
  - frontend/src/main.ts
  - frontend/src/style.css
  - frontend/src/api.ts
  - frontend/src/api.test.ts
  - frontend/src/placement.ts
  - frontend/src/placement.test.ts
  - frontend/src/App.vue
  - frontend/src/App.test.ts
  - frontend/src/components/PdfDocument.vue
  - frontend/src/components/PdfPage.vue
  - frontend/src/components/PdfPage.test.ts
  - frontend/src/components/SignatureOverlay.vue
  - frontend/src/components/SignatureContextMenu.vue
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Human review needs a deliberately minimal browser surface that edits the same normalized placement state used by automatic signing. Build the Vue 3/PDF.js interface without introducing browser-side persistence, arbitrary paths, or separate suggested/manual placement concepts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 PDF.js renders every page into a canvas inside a relatively positioned displayed-page container, with PNG overlays above it and no dependence on browser zoom or render resolution
- [x] #2 The only normal visible toolbar controls are `Place signature` and `Save`, and saving never prompts for a filename or initiates a browser download
- [x] #3 Place mode adds one centered, bounds-clamped signature on the next page click using configured normalized width and the PNG physical/display aspect ratio, then exits place mode
- [x] #4 Every preloaded or newly added overlay supports bounds-safe movement, aspect-locked resizing, selection, right-click removal through the custom one-command menu, and selected-item Delete-key removal
- [x] #5 A validated input profile initializes the same editable placement collection, while a session without coordinates starts empty
- [x] #6 Save is disabled until at least one valid placement exists, submits only placements, and shows a minimal Saved confirmation after backend success
- [x] #7 Vitest covers placement state and coordinate math, including clamping, aspect ratio, add, move, resize, selection, and removal behavior
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Scaffold an isolated Vue 3/Vite TypeScript frontend using a Node-20-compatible PDF.js release and same-origin API helpers.
2. Implement one pure normalized placement-state module for initialization, validation, physical/display aspect sizing, clamped add/move/resize, selection, and removal.
3. Render every PDF.js page into a responsive high-DPI canvas and layer the shared PNG placements as percentage-based DOM overlays.
4. Add the one-shot placement, pointer drag/resize, selection, custom context removal, Delete removal, preload, and placements-only save interactions behind the exact two-control toolbar.
5. Add focused Vitest coverage for state and coordinate math, then run frontend typecheck/build/tests and the full Python coverage/lint/type suite.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Confirmed implementation: frontend/src/placement.ts is the single immutable normalized state/math boundary for preloaded and new placements. PDF.js rotated viewport dimensions and PNG intrinsic dimensions compute normalized physical aspect as height = width / imageAspect * pageWidth / pageHeight, matching backend stamping validation. PdfPage renders responsive device-pixel-aware canvases and percentage overlays; App owns one-shot placement, selection, removal, and placements-only save state. Touch users can drag/resize and long-press an overlay for the same one-command removal menu.

Dependency constraint: repository Node is 20.19.2. pdfjs-dist 5.6.205 was rejected after npm audit identified GHSA-hq66-cqwq-w95j; patched 6.x requires Node 22. The frontend pins audit-clean pdfjs-dist 5.4.624.

Verification evidence: npm run typecheck passed; npm test passed 12 tests across 4 files covering physical/display aspect math, edge clamping, add/move/resize, state initialization/selection/removal/validity, canvas render invocation and percentage overlays, exact toolbar controls, one-shot mode, preloading, Delete/custom-menu removal, save enablement, placements-only API payload, and Saved confirmation; npm run build produced the application and bundled PDF.js worker; npm audit reported 0 vulnerabilities. Full backend regression checks passed: 183 pytest tests with 100% coverage, ruff check, ruff format --check, and mypy. git diff --check passed.

Scoped limitation: browser/server lifecycle, copying the Vite build into the Python package, and real-browser Playwright E2E remain intentionally deferred to TASK-001.10. No ADR was needed and there are no blockers for this subtask.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @human
created: 2026-09-04 20:04
---
Implement only the Vue 3 + Vite + PDF.js review interface in this subtask; lifecycle/CLI integration and Playwright end-to-end coverage remain scoped to TASK-001.10.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the Vue 3/Vite review frontend with PDF.js page canvases, responsive normalized PNG overlays, a unified placement state, physical-aspect sizing, bounds-safe add/move/resize, selection and keyboard/context removal, preload support, and a minimal placements-only save flow. Added 12 focused Vitest tests and an audit-clean Node-20 dependency lock. Verified frontend typecheck, tests, production build, and npm audit; verified all 183 Python tests at 100% coverage plus Ruff formatting/lint and mypy. No known subtask blocker. Packaging/lifecycle and Playwright remain with TASK-001.10; no ADRs created.
<!-- SECTION:FINAL_SUMMARY:END -->
