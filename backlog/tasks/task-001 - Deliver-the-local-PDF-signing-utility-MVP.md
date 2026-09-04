---
id: TASK-001
title: Deliver the local PDF signing utility MVP
status: To Do
assignee: []
created_date: '2026-09-04 18:02'
updated_date: '2026-09-04 18:39'
labels: []
dependencies: []
references:
  - docs/pdf-sign-implementation-spec.md
priority: high
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The checked-in package is the intentional initial scaffold for PDF Signoff, a local agent-friendly utility that visually stamps signature PNGs onto PDFs, optionally seals the result cryptographically, and supports either explicit unattended placement or browser-based human review. This parent tracks the complete initial product boundary; focused child tasks extend the existing Click/Onacol foundation in reviewable delivery units.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The installed `pdf-signoff` command supports explicit headless L0 signing and browser-based review while never modifying the input PDF
- [ ] #2 Every successful signing operation writes a deterministic separate output and emits exactly one final placement-profile JSON object on stdout, with diagnostics confined to stderr
- [ ] #3 Reusable normalized placements work across browser zoom levels and tested PDF page rotations, CropBoxes, origins, and dimensions
- [ ] #4 L1 output contains the L0 visual placements plus an intact invisible PDF digital signature
- [ ] #5 Unsupported inputs, mismatched profiles, signed inputs without override, and output conflicts fail conservatively without partial output
- [ ] #6 The local review server is loopback-only and session-protected, and the complete CLI, geometry, stamping, review, and L1 workflows have automated coverage
<!-- AC:END -->
