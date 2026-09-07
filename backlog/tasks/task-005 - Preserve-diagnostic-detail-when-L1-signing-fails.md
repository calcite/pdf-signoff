---
id: TASK-005
title: Preserve diagnostic detail when L1 signing fails
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:25'
updated_date: '2026-09-07 09:27'
labels:
  - code-review
dependencies: []
references:
  - pdf_signoff/crypto.py
  - pdf_signoff/cli.py
modified_files:
  - pdf_signoff/crypto.py
  - tests/test_crypto.py
priority: medium
type: enhancement
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`L1Signer.sign` catches every exception from pyHanko and re-raises `L1SigningError("Cryptographic PDF signing failed.")`. `main` renders only `str(exc)` through `ClickException`, so the operator receives that one sentence regardless of cause. An expired certificate, an unsupported key algorithm, a malformed incremental-update revision, and a full disk are indistinguishable.

The secret-safety instinct is correct and must be kept: pyHanko messages can reference credential paths and signer details. But exception class names and pyHanko error categories are not secrets, and without them a failed L1 run is undiagnosable from the terminal.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A failed L1 signature reports enough to distinguish credential, certificate, PDF-structure, and I/O causes
- [x] #2 No message path can print the PKCS#12 password, private-key bytes, or the credential file contents
- [x] #3 The original exception remains chained so a traceback is available at higher verbosity
- [x] #4 Tests assert both that the cause category is reported and that the password never appears in any output stream
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Classify exceptions raised while adding an L1 signature into a stable, secret-safe credential, certificate, PDF-structure, I/O, or unexpected category.
2. Keep the original exception chained while reporting only the category and exception class, never arbitrary exception text.
3. Add tests for category reporting, exception chaining, CLI output, and password redaction; run focused and full quality checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Investigation found L1Signer already chained the original exception but discarded all diagnostic detail. Exception text can expose credential paths or signer details, so reporting is limited to typed categories and class names.

Verification: .venv/bin/tox passed lint, formatting, mypy, 225 tests, and the configured 100% coverage gate. Category tests cover InvalidKey, InvalidCertificateError, PdfReadError, and OSError; the CLI regression proves a password-bearing failure is absent from stdout and stderr.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-07 09:24
---
Agent: Implementation and verification are complete; task is ready for human review.
---

author: @human
created: 2026-09-07 09:27
---
Human: Confirmed the implementation was checked and requested task closure.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Changed L1Signer.sign to report secret-safe credential, certificate, PDF structure, I/O, or unexpected categories with the exception class while preserving exception chaining. Added category, redaction, rollback, and chaining tests. Verified with .venv/bin/tox: lint, formatting, mypy, 225 tests, and 100% coverage passed. No limitations, follow-up tasks, or ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
