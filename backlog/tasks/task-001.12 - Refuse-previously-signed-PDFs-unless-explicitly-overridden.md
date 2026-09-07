---
id: TASK-001.12
title: Refuse previously signed PDFs unless explicitly overridden
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:04'
updated_date: '2026-09-07 07:11'
labels: []
dependencies:
  - TASK-001.07
references:
  - docs/pdf-sign-implementation-spec.md#16-existing-digital-signatures-on-input
modified_files:
  - pdf_signoff/inspection.py
  - pdf_signoff/cli.py
  - pdf_signoff/server.py
  - pdf_signoff/crypto.py
  - tests/test_inspection.py
  - tests/test_cli.py
  - tests/test_crypto.py
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Stamping or rewriting a cryptographically signed input can invalidate prior signatures. Detect this condition before either automatic processing or browser launch and require an expert override so normal workflows cannot silently damage an existing signature.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Input inspection detects existing cryptographic PDF signatures before opening the review UI or modifying any output
- [x] #2 A signed input is refused by default with an error explaining that stamping may invalidate prior signatures
- [x] #3 `--allow-signed-input` permits processing and emits a strong warning only to stderr
- [x] #4 Override output and messaging make no claim that any previous signature remains valid
- [x] #5 Tests use a digitally signed fixture to verify default refusal, no partial output or stdout profile, and successful override with warning in supported signing modes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend PDF inspection with pyHanko's signature-field traversal to report whether any filled cryptographic signature field exists, treating signature-structure inspection failures as unsafe input without performing validity or trust validation.
2. Inspect once in common CLI startup before credential loading or mode dispatch, refuse signed inputs by default, and emit an explicit stderr-only expert-override warning when allowed; pass the inspection into automatic and review setup so neither path launches UI or writes output first.
3. Add generated cryptographically signed test inputs covering default refusal and override behavior across review/automatic and L0/L1 modes, plus conservative handling of a malformed filled signature dictionary.
4. Run focused and full Python tests with coverage, Ruff checks/format, mypy, package build, and CLI smoke checks; synchronize task evidence while leaving it In Progress for human acceptance.

Implementation adjustment: when L1 override processing encounters the utility's existing fixed signature field name, select the next unused deterministic field name before adding the new integrity signature; pyHanko correctly refuses to overwrite a filled field.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation: `inspect_pdf` currently validates PDF readability/geometry/text/hash with MuPDF but does not inspect signature fields. The CLI option and `Invocation.allow_signed_input` already exist but are unused. Automatic mode calls `inspect_pdf` before stamping; review mode calls it in `prepare_review_session` before server/browser creation. Common CLI dispatch currently loads L1 credentials before either inspection. pyHanko exposes public `enumerate_sig_fields(reader, filled_status=True)`, which detects filled regular and document-timestamp signature fields without validation/trust work and does not ignore unknown or malformed signature dictionaries merely because their `/SubFilter` or `/ByteRange` is invalid.

Focused matrix finding: L0 override succeeds, but L1 override of a PDF previously signed by this utility initially failed because `L1Signer.sign` always requested the already-filled `PdfSignoffIntegrity` field. Override support requires selecting an unused field name for the new L1 signature; this remains signature creation, not prior-signature validation.

Final verification evidence (2026-09-04): generated pyHanko-signed inputs were exercised through auto/review x L0/L1. Every default invocation exited 1 with empty stdout, an invalidation-risk explanation, no review dispatch, no output, and no temp artifact. Every override invocation completed with a JSON profile on stdout, a strong warning and save message on stderr, and a committed PDF. A generated signature with a deliberately malformed `/ByteRange` key remained detected; parser/traversal failures are rejected as unsafe. Full suite: 213 passed with 100.00% coverage (`.venv/bin/pytest --cov=pdf_signoff --cov-report=term-missing tests/`). Static checks: `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and `.venv/bin/mypy pdf_signoff` passed. Packaging: `uv build` produced both sdist and wheel. CLI smoke: `.venv/bin/pdf-signoff --help` passed and showed the expert override. Installed-wheel smoke passed auto and real review-server/browser-callback flows without Node on PATH. Frontend regressions were not run because no frontend source or bundled asset changed. The sole test warning is Starlette's existing anyio `BlockingPortal` deprecation.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Human
created: 2026-09-07 07:11
---
The human reviewed the implementation and confirmed it works; accepted for completion.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented pre-work cryptographic-signature detection and refusal for signed input PDFs. `inspect_pdf` now uses pyHanko signature-field traversal without signature validation or trust management; common CLI startup applies the policy before L1 credential loading, mode dispatch, browser launch, stdout profile emission, or output writes. `--allow-signed-input` proceeds only with an explicit stderr warning that modification may invalidate prior signatures and makes no validity claim. L1 signing now chooses an unused deterministic signature-field name so override processing also works on PDFs previously signed by this utility. Generated signed-input tests cover auto/review and L0/L1 refusal/override behavior, artifacts/stdout/stderr, malformed signature dictionaries, and conservative inspection failures. Verification: 213 tests passed at 100% coverage; Ruff lint/format, mypy, sdist/wheel builds, CLI help, and isolated installed-wheel auto/review smoke passed. Known limitation by design: detection identifies filled standard PDF signature fields and does not assess cryptographic validity, certificate trust, or preservation of prior signatures. No frontend changes, follow-up tasks, or ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
