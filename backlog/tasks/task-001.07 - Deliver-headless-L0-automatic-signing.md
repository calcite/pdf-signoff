---
id: TASK-001.07
title: Deliver headless L0 automatic signing
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:03'
updated_date: '2026-09-07 07:11'
labels: []
dependencies:
  - TASK-001.02
  - TASK-001.05
  - TASK-001.06
references:
  - docs/pdf-sign-implementation-spec.md#14-l0-implementation
  - docs/pdf-sign-implementation-spec.md#20-3-auto-mode
  - docs/pdf-sign-implementation-spec.md#22-tests
modified_files:
  - pdf_signoff/cli.py
  - pdf_signoff/stamping.py
  - tests/test_cli.py
  - tests/test_stamping.py
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Milestone 1 needs an end-to-end unattended path that applies validated profile placements through the shared backend pipeline. This is the first usable product slice and establishes the stdout/stderr process contract consumed by external agents.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Explicit `--auto` with a matching non-empty profile embeds the PNG at every placement and writes the resolved output PDF
- [x] #2 PNG transparency is preserved, multiple placements and pages are supported, and clearly inconsistent physical rectangle aspect ratios are rejected rather than distorted
- [x] #3 L0 output contains visual image placements without adding a cryptographic signature or proprietary Adobe Fill & Sign metadata
- [x] #4 A successful command emits exactly one final profile JSON document on stdout, sends status and logs only to stderr, and exits zero
- [x] #5 A failed command emits no profile JSON, exits non-zero, and leaves neither a partial output nor a modified input
- [x] #6 Integration tests reopen and render synthetic outputs to verify expected signature regions, transparency, multiple pages, and unchanged input hashes; CLI tests enforce stdout, stderr, and exit-code behavior
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Implement the shared L0 stamping boundary in `pdf_signoff/stamping.py`: validate every placement's displayed physical aspect ratio against the decoded PNG with a documented tolerance, convert only through `placement_to_pdf_rect`, compensate for page display rotation, preserve PNG alpha, save through `write_output_atomically`, and normalize PyMuPDF/file failures without adding crypto or proprietary metadata.
2. Wire only explicit automatic L0 invocations in `pdf_signoff/cli.py` through conservative PDF/PNG inspection, auto-mode profile loading, profile/document matching, transactional stamping, and final-profile rebuilding; emit one compact JSON document to stdout only after commit, status to stderr, and convert expected failures to non-zero Click errors with empty stdout. Preserve review and L1 as existing handoff seams.
3. Add direct integration tests using synthetic PDFs and RGBA PNGs that reopen and render outputs, cover transparency, multiple placements/pages and rotated pages, verify image orientation/regions, reject malformed aspect ratios, assert no PDF signatures/proprietary Adobe metadata, preserve input hashes, and prove failed writes clean temporary output.
4. Extend CLI tests with real fixtures for exact success stdout/stderr/exit behavior, refreshed profile metadata, deterministic output, profile mismatch/aspect/stamping failures, and no partial or modified input.
5. Run focused and full pytest with 100% coverage, Ruff format/lint, mypy, tox, lock/build checks, and installed/current CLI smoke tests; synchronize task evidence and leave it In Progress for human acceptance.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation: prerequisites TASK-001.02 through TASK-001.06 are implemented and the baseline is 134 tests at 100% project coverage with Ruff and mypy clean. `cli.main` currently validates and returns an immutable `Invocation`; review and L1 have no implementation. `stamping.py` is an empty boundary. Existing shared code provides conservative PDF/PNG inspection, strict auto profile loading, profile matching, the sole displayed-CropBox converter, final-profile rebuilding, output resolution, and same-directory atomic publication.

PyMuPDF 1.28.2 requires page-operation rectangles in unrotated coordinates. Synthetic probing confirmed that `placement_to_pdf_rect` supplies those coordinates and `insert_image(..., rotate=page.rotation, keep_proportion=True)` preserves the PNG's upright displayed orientation and fills a physically matching rectangle on rotations 0/90/180/270. PyMuPDF preserves PNG alpha when inserting its encoded stream. Existing-signature policy is explicitly TASK-001.12 and remains out of scope; L1 crypto is TASK-001.11 and review is TASK-001.08 onward.

Implementation result: `stamp_l0` is the shared visual persistence seam. It validates every normalized placement against current displayed page dimensions and the decoded PNG ratio with a 5% relative tolerance, reads the encoded PNG once, converts each placement only with `placement_to_pdf_rect`, reuses the embedded image xref, rotates image content with `page.rotation` so it remains upright in displayed coordinates, and saves through the same-directory atomic writer. PyMuPDF errors are normalized as `StampingError`; all aspect checks happen before output creation.

The Click path executes only explicit `--auto` L0 invocations. Conservative startup inspects the PDF and PNG, requires a non-empty strict profile, verifies page geometry/rotation/text matching, then stamps and commits before rebuilding current SHA-256/page metadata and emitting compact JSON. Expected startup/stamping/output failures become Click errors with empty stdout. Success emits exactly one JSON document plus newline to stdout and exactly `Saved signed PDF: <path>` plus newline to stderr. Existing review and L1 invocation handoffs remain unchanged for TASK-001.08/TASK-001.10 and TASK-001.11; existing-signature refusal remains TASK-001.12. No crypto or Adobe proprietary metadata was added.

Verification evidence: focused stamping/CLI tests passed 28/28. Full `uv run pytest --cov=pdf_signoff --cov-report=term-missing tests/` passed 146/146 at 100% project coverage. Rendered synthetic checks prove transparent pixels reveal pre-existing green page content, opaque asymmetric red/blue regions render at expected coordinates and upright orientation, two placements share page 1, and a third renders on rotated page 2. Reopened outputs have no signature flags, `/Type/Sig`, or `ADBE_FillSign`; source SHA-256 remains unchanged. Aspect mismatch, profile mismatch, malformed profile, PNG read failure, and injected insertion failure tests prove non-zero/empty-stdout behavior and output/temp cleanup. `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy pdf_signoff`, `git diff --check`, and `uv lock --check` passed. Both `uv run tox` environments passed, `uv build` produced sdist/wheel, current CLI help passed, and a fresh Python 3.13 environment installed the wheel and completed a real auto-L0 command with one parseable stdout profile, exact stderr status, and a reopenable stamped output. No blockers, dependency changes, ADRs, or new follow-up tasks.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @human
created: 2026-09-04 19:47
---
**Human:** Implement only TASK-001.07 from a fresh context; prerequisites through TASK-001.06 are implemented and verified but remain In Progress pending acceptance. Deliver explicit automatic L0 end to end with conservative startup, profile matching, aspect validation, shared geometry, transactional output, final profile and exact process contracts; exclude review, L1, proprietary Adobe metadata, and crypto except clean seams.
---

author: Human
created: 2026-09-07 07:11
---
The human reviewed the implementation and confirmed it works; accepted for completion.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Delivered the explicit headless L0 workflow end to end. Automatic L0 now performs conservative PDF/PNG inspection, strict profile loading and matching, 5%-tolerant physical aspect validation, upright alpha-preserving PyMuPDF insertion through the sole geometry converter, transactional publication, refreshed final-profile construction, and the exact machine-readable stdout/human-readable stderr contract. Review, L1, existing-signature policy, cryptography, and Adobe proprietary metadata remain outside this subtask.

Added synthetic render integration coverage for transparency, expected regions, repeated placements, multiple and rotated pages, unsigned/non-proprietary output, unchanged source hashes, malformed aspects, and failed-write cleanup, plus real CLI success/failure contract tests. Verified 146 tests at 100% coverage, Ruff format/lint, mypy, diff/lock checks, both tox environments, package build, CLI help, and a fresh-wheel installed auto-L0 smoke. No known blockers, ADRs, dependency changes, or new follow-up tasks. Task remains In Progress for human acceptance.
<!-- SECTION:FINAL_SUMMARY:END -->
