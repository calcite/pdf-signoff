---
id: TASK-001
title: Deliver the local PDF signing utility MVP
status: In Progress
assignee:
  - '@opencode'
created_date: '2026-09-04 18:02'
updated_date: '2026-09-04 21:07'
labels: []
dependencies: []
references:
  - docs/pdf-sign-implementation-spec.md
  - README.md
priority: high
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PDF Signoff is a local Python 3.13 utility delivered through the installed `pdf-signoff` Click command and schema-backed Onacol YAML configuration. It places one PNG signature at reusable normalized coordinates through either the default protected browser review workflow or explicit unattended `--auto` mode, always writes a separate transactional output, and emits the final version-1 placement profile on stdout. Optional L1 processing adds an invisible pyHanko integrity signature over the complete L0-stamped revision. This parent tracks the delivered MVP product boundary and its documented security, input, trust, and workflow limitations across the 13 focused child tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The installed `pdf-signoff` command supports explicit headless L0 signing and browser-based review while never modifying the input PDF
- [x] #2 Every successful signing operation writes a deterministic separate output and emits exactly one final placement-profile JSON object on stdout, with diagnostics confined to stderr
- [x] #3 Reusable normalized placements work across browser zoom levels and tested PDF page rotations, CropBoxes, origins, and dimensions
- [x] #4 L1 output contains the L0 visual placements plus an intact invisible PDF digital signature
- [x] #5 Unsupported inputs, mismatched profiles, signed inputs without override, and output conflicts fail conservatively without partial output
- [x] #6 The local review server is loopback-only and session-protected, and the complete CLI, geometry, stamping, review, and L1 workflows have automated coverage
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Read the parent and all 13 child records, including criteria, implementation notes, and final evidence, without changing child acceptance state.
2. Compare the parent contract with the current Click/Onacol package, README, frontend assets, cross-cutting tests, and installed-wheel evidence.
3. Run only targeted checks needed to confirm that current critical paths still agree with the latest comprehensive release evidence.
4. Correct stale parent wording, record distilled audit findings, check only objectively supported parent criteria, and leave all tasks awaiting human acceptance.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Clean-context completion audit (2026-09-04): reviewed AGENTS.md; Backlog overview, execution, and finalization guidance; TASK-001; and all 13 children with their checked criteria, notes, and final summaries. Inspected the current Click/Onacol CLI and defaults, profile/inspection/geometry/output/stamping/crypto/server modules, README, packaged Vue/PDF.js assets, Playwright workflow, and isolated-wheel smoke. The original parent description still called the completed package an initial scaffold, so it was updated to state the delivered Python 3.13 `pdf-signoff` Click/Onacol product boundary; the six parent criteria already match implemented behavior and required no wording changes.

Latest comprehensive evidence is sufficient: TASK-001.13 records 213 Python tests with 100% coverage, 12 Vitest tests, 2 Chromium Playwright workflows, Ruff, mypy, tox, frozen lock/sync, npm audit/typecheck/build, sdist/wheel inspection, and a final isolated Python 3.13 wheel smoke covering auto, review, L1, security, overwrite, stdout isolation, and signed-input protection with Node absent. Targeted current-tree confirmation passed 22 tests spanning automatic output/profile behavior, review lifecycle, all rotations and offset CropBoxes, transactional cleanup/overwrite preservation, unauthorized/cross-origin/loopback review security, L1 integrity and tamper detection, and signed-input refusal/override. `uv lock --check` resolved 65 packages and `uv run pdf-signoff --help` exposed the expected command contract.

No code or documentation defect, release blocker, new dependency, or missing ADR was found. Residual limitations are documented product boundaries: loopback HTTP uses an HttpOnly SameSite=Strict but non-Secure cookie; required-text matching has no OCR; L1 supplies revision integrity but no certificate trust, timestamping, revocation/LTV, legal identity, or assurance that overridden prior signatures remain valid. The Python checks retain one upstream Starlette AnyIO `BlockingPortal` deprecation warning. No follow-up task is required from this audit.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completion audit result: all six parent acceptance criteria are supported by current implementation and objective child/release evidence. Updated only the stale parent description and references so the canonical task names the delivered Python 3.13 Click/Onacol `pdf-signoff` product rather than an initial scaffold; no application code, product documentation, child task state, or checked child criterion changed.

Implementation choices: retained the 13-child decomposition and current MVP boundaries; relied on the latest comprehensive final-artifact evidence where sufficient and used a narrow current-tree regression selection rather than re-running or reimplementing every subtask.

Tests and checks: reviewed every child final summary/evidence; inspected current backend, CLI/configuration, README, packaged frontend, Playwright, and isolated-wheel smoke; ran 22 targeted Python tests successfully, `uv lock --check` successfully (65 packages), and `uv run pdf-signoff --help` successfully. TASK-001.13 remains the comprehensive evidence source: 213 Python tests at 100% coverage, 12 Vitest tests, 2 Playwright E2E workflows, lint/type/tox/build/package checks, and a Node-free installed-wheel auto/review/L1/security/signature-guard smoke.

Known limitations: one upstream Starlette AnyIO deprecation warning; non-Secure session cookie on trusted loopback HTTP; no OCR, trust/identity validation, timestamping, revocation/LTV, legal-signature claim, or guarantee that expert-override processing preserves prior signatures. These are documented non-goals or operating constraints, not release blockers.

Follow-ups: none identified. ADRs: none created or missing. TASK-001 and all children remain In Progress for human acceptance.
<!-- SECTION:FINAL_SUMMARY:END -->
