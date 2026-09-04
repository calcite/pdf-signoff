---
id: TASK-001.09
title: Build the Vue PDF placement interface
status: To Do
assignee: []
created_date: '2026-09-04 18:03'
labels: []
dependencies:
  - TASK-001.08
references:
  - docs/pdf-sign-implementation-spec.md#10-interactive-web-ui
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
- [ ] #1 PDF.js renders every page into a canvas inside a relatively positioned displayed-page container, with PNG overlays above it and no dependence on browser zoom or render resolution
- [ ] #2 The only normal visible toolbar controls are `Place signature` and `Save`, and saving never prompts for a filename or initiates a browser download
- [ ] #3 Place mode adds one centered, bounds-clamped signature on the next page click using configured normalized width and the PNG physical/display aspect ratio, then exits place mode
- [ ] #4 Every preloaded or newly added overlay supports bounds-safe movement, aspect-locked resizing, selection, right-click removal through the custom one-command menu, and selected-item Delete-key removal
- [ ] #5 A validated input profile initializes the same editable placement collection, while a session without coordinates starts empty
- [ ] #6 Save is disabled until at least one valid placement exists, submits only placements, and shows a minimal Saved confirmation after backend success
- [ ] #7 Vitest covers placement state and coordinate math, including clamping, aspect ratio, add, move, resize, selection, and removal behavior
<!-- AC:END -->
