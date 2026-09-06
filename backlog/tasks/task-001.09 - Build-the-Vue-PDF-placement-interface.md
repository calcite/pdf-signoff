---
id: TASK-001.09
title: Build the Vue PDF placement interface
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:03'
updated_date: '2026-09-05 06:22'
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
Human review uses a deliberately minimal browser surface that edits the same normalized placement state used by automatic signing. Build the Vue 3/PDF.js interface without browser-side persistence, arbitrary paths, or separate suggested/manual placement concepts. During one-shot placement, show the signature PNG itself as a bounds-clamped preview instead of a crosshair. A resize sets the session-local normalized width for all later placements; the initial value remains the configured default.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 PDF.js renders every page into a canvas inside a relatively positioned displayed-page container, with PNG overlays above it and no dependence on browser zoom or render resolution
- [x] #2 The only normal visible toolbar controls are Place signature and Save, and saving never prompts for a filename or initiates a browser download
- [x] #3 Place mode shows a non-interactive PNG preview under the pointer, bounds-clamped exactly as the final centered placement, and a page click adds one signature then exits place mode
- [x] #4 New placements use the configured normalized width initially; each completed resize updates the session-local normalized width used for all later placements, including on differently sized pages
- [x] #5 Every preloaded or newly added overlay supports bounds-safe movement, aspect-locked resizing, selection, right-click removal through the custom one-command menu, and selected-item Delete-key removal
- [x] #6 A validated input profile initializes the same editable placement collection, while a session without coordinates starts empty
- [x] #7 Save is disabled until at least one valid placement exists, submits only placements, and shows a minimal Saved confirmation after backend success
- [x] #8 Vitest and Playwright cover preview geometry, remembered resize width, placement state, coordinate math, and the primary review workflow
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Share centered, aspect-locked, bounds-clamped placement rectangle calculation between new placement creation and cursor preview. 2. Keep a session-local current placement width in App, initialized from defaultSignatureWidth and updated from each clamped resize result. 3. Pass the current width to PDF pages and render a pointer-driven, non-interactive signature PNG preview during place mode. 4. Ensure overlay interactions do not prevent a placement click while place mode is active and remove the crosshair cursor. 5. Add unit, component, and real-browser coverage for preview clamping and remembered widths. 6. Document the revised placement behavior, rebuild packaged frontend assets, and run frontend plus Python verification.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation: frontend/src/placement.ts now exposes centeredPlacement, the shared centered, aspect-locked, bounds-clamped geometry used by both placement creation and the page preview. App stores a session-local placementWidth initialized from the server default and updates it from the actual clamped width after every resize. PdfPage renders a non-interactive PNG preview under mouse pointers in place mode, clears it on exit or placement, suppresses normal overlay interaction while placing, and hides the native cursor. Touch placement remains click/tap based without a hover preview.

The remembered width is a normalized displayed-page-width fraction. It is deliberately session-local and is neither sent in the save payload nor persisted to configuration.

Verification: npm test passed 16 Vitest tests; npm run typecheck and npm run build passed; npm run test:e2e passed both Chromium workflows against the actual CLI; npm audit reported 0 vulnerabilities. uv run pytest --cov=pdf_signoff tests/ passed 213 tests at 100% coverage; Ruff lint/format checks, mypy, uv lock --check, and git diff --check passed.

No ADR, blockers, limitations, or follow-up tasks were identified.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @human
created: 2026-09-04 20:04
---
Implement only the Vue 3 + Vite + PDF.js review interface in this subtask; lifecycle/CLI integration and Playwright end-to-end coverage remain scoped to TASK-001.10.
---

author: @human
created: 2026-09-05 06:15
---
Human: Approved a DOM-based PNG placement preview, clamped fully within page bounds. A completed resize sets the session-local normalized page-width fraction for subsequent placements, including on differently sized pages.
---

author: @opencode
created: 2026-09-05 06:21
---
Agent: Implementation and verification are complete; task is ready for human review.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Replaced the placement crosshair with an exact, bounds-clamped PNG preview and made the latest clamped resize width the session-local default for subsequent placements. Shared placement/preview geometry prevents divergence, while page-aware height calculation preserves the PNG physical aspect on every page. Updated documentation, rebuilt packaged web assets, and extended Vitest plus real Chromium coverage. Verified: 16 Vitest tests, frontend typecheck/build, 2 Playwright workflows, npm audit, 213 Python tests at 100% coverage, Ruff, mypy, lock validation, and git diff --check. No known limitations, follow-up tasks, or ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
