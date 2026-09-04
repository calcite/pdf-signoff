---
id: TASK-001.11
title: Add L1 cryptographic integrity signing
status: In Progress
assignee:
  - '@opencode'
created_date: '2026-09-04 18:04'
updated_date: '2026-09-04 20:46'
labels: []
dependencies:
  - TASK-001.07
references:
  - docs/pdf-sign-implementation-spec.md#15-l1-implementation
  - docs/pdf-sign-implementation-spec.md#22-3-l1-integration-tests
modified_files:
  - pdf_signoff/crypto.py
  - pdf_signoff/stamping.py
  - pdf_signoff/cli.py
  - pdf_signoff/server.py
  - tests/test_crypto.py
  - tests/test_cli.py
  - tests/test_config.py
  - tests/test_server.py
parent_task_id: TASK-001
priority: medium
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Some approvals need tamper evidence in addition to the visible PNG. Add an optional second stage that signs the completed L0 revision with a configured PKCS#12 credential while keeping identity assurance, timestamping, and long-term validation explicitly outside the product claim.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `--level l1` first creates the same approved visual result as L0 and then applies an invisible pyHanko PDF signature over that complete revision
- [x] #2 A configured `.p12` or `.pfx` signer and reason are loaded after path expansion, with the password read from the configured environment variable and any TTY fallback using a secure prompt
- [x] #3 Passwords, private-key material, and sensitive signer data never appear in command arguments, stdout, stderr, or logs
- [x] #4 Missing or invalid signer credentials fail clearly without committing output or emitting profile JSON
- [x] #5 Tests using generated self-signed credentials verify cryptographic integrity despite untrusted certificate status, preservation of the visual PNG, and failed integrity after tampering
- [x] #6 The implementation does not add a visible cryptographic field appearance, TSA timestamping, revocation embedding, trust management, or claims of verified human identity
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a secret-safe L1 credential boundary that reads the expanded Onacol YAML PKCS#12 path, obtains the passphrase from only the configured environment variable or a secure TTY getpass fallback, loads the in-memory bundle without pyHanko path/exception logging, and returns clear sanitized failures.
2. Extend the shared stamping transaction with an optional finalization callback; for L1, incrementally add a pyHanko approval signature with configured reason to the fully stamped temporary PDF before the existing atomic publication step.
3. Resolve L1 credentials once during CLI startup and inject the signing callback into both automatic and review session save paths, preserving empty stdout and no committed/temporary output on credential or signing failure.
4. Add generated self-signed PKCS#12 integration coverage for automatic and review workflows, signature revision integrity/untrusted status, visual PNG preservation, tamper detection, path expansion/reason/password-source behavior, secret-safe diagnostics, and failure atomicity.
5. Run focused and full Python suites at 100% coverage, frontend regressions only if frontend files change, Ruff lint/format, mypy, lock/diff checks, tox, build, and current plus isolated-wheel CLI smokes; then finalize task evidence while leaving it In Progress.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation (2026-09-04): `stamp_l0` owns the shared `write_output_atomically` callback and currently publishes immediately after PyMuPDF saves; `ReviewSession.save` and `_run_automatic_l0` both call it. L1 therefore must run against that same temporary path before publication to cover the complete stamped revision and preserve failure atomicity. Bundled Onacol YAML already defines `l1.pkcs12_path`, `password_env`, and `reason`, and config loading expands environment variables and `~` in the signer path. Installed pyHanko is 0.37.0: `SimpleSigner.load_pkcs12_data` loads in-memory bytes and raises without logging file paths, while `IncrementalPdfFileWriter` plus `PdfSigner(...).sign_pdf(..., in_place=True)` provides the required incremental signature. Omitting a field box/stamp style creates an invisible field; no timestamper or validation context is needed. Validation exposes separate `intact`, `valid`, and `trusted` status, allowing self-signed tests to prove integrity while remaining untrusted.

Implementation checkpoint: `crypto.py` now loads expanded `.p12`/`.pfx` bytes through `SimpleSigner.load_pkcs12_data`, obtains the passphrase only from the configured environment variable or TTY-gated `getpass`, and wraps credential/signing failures in fixed path/password/key-safe diagnostics. `stamp_l0` runs an optional finalizer after PyMuPDF closes the complete stamped temporary revision but before atomic publication; both automatic and review flows inject the invisible pyHanko signer there. The review save route is synchronous so FastAPI runs its existing blocking PDF/file pipeline in a worker thread, avoiding pyHanko 0.37.0 synchronous `asyncio.run` conflicts. The signature field has a zero rectangle and no stamp style; no timestamper, validation context, trust store, revocation data, or identity claim was added.

Verification evidence (2026-09-04): `uv run pytest tests/test_crypto.py --cov=pdf_signoff.crypto --cov-report=term-missing --cov-fail-under=100` passed 15/15 at 100%; `uv run pytest --cov=pdf_signoff --cov-report=term-missing tests/` passed 206/206 at 100.00%. Generated RSA/SHA-256 self-signed PKCS#12 tests prove automatic and protected-review L1 output, whole-file signature coverage, intact/valid cryptography with `trusted == false`, identical L0/L1 page renders with the PNG present, configured reason, zero-area invisible field, no timestamp signatures, and `intact == false` after covered-byte tampering. Tests also prove env precedence, secure TTY prompt fallback, missing/non-TTY/wrong/unreadable/invalid credentials, secret-safe stderr/logs, empty stdout, prior-output preservation, temporary cleanup, post-stamp rollback, and sanitized review API failures.

Repository checks passed: `uv run ruff check .`; `uv run ruff format --check .` (24 files); `uv run mypy pdf_signoff` (10 source files); `uv lock --check`; `git diff --check`; and `uv run tox` (lint and py313, 206 tests at 100%). `uv build` produced `dist/pdf_signoff-0.1.0.tar.gz` and `dist/pdf_signoff-0.1.0-py3-none-any.whl`. Current-source and fresh-wheel `pdf-signoff --help`, `--get-config-template -`, and real auto-L1 CLI smokes passed using an environment-expanded PKCS#12 path; both outputs independently validated as intact/valid and self-signed untrusted. Frontend regressions were not run because no frontend files or contracts changed. One pre-existing upstream Starlette `BlockingPortal` deprecation warning remains. No blockers, ADRs, dependency changes, or follow-up tasks; timestamping, revocation/LTV, trust/legal identity, visible cryptographic appearance, and existing-signature policy remain out of scope.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-04 20:34
---
Human: Implement TASK-001.11 only. Add invisible L1 signing over the complete L0-stamped revision for auto and review workflows, including specified Onacol credential configuration, secure secret handling, transactional failures, generated-credential integration tests, and full verification. Keep timestamping, trust/legal identity, and visible cryptographic appearance out of scope; leave the task In Progress for human acceptance.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented L1 as a secret-safe invisible pyHanko approval signature over the complete L0-stamped temporary revision, shared by automatic and review workflows before atomic output publication. Reused the schema-backed Onacol YAML signer settings with expanded PKCS#12 paths, environment-only passwords plus secure TTY fallback, configured reason metadata, sanitized errors, and rollback on every credential/signing failure. Added generated self-signed integration coverage for full-revision integrity, explicit untrusted status, unchanged visual rendering, tamper detection, both workflows, secret handling, and transactional output behavior. Verified 15 focused tests and 206 full tests at 100% coverage, Ruff, mypy, lock/diff checks, tox, build, and current/fresh-wheel real L1 CLI smokes. No frontend changes, blockers, ADRs, dependency changes, or follow-ups; one upstream Starlette deprecation warning remains. Task intentionally remains In Progress for human acceptance.
<!-- SECTION:FINAL_SUMMARY:END -->
