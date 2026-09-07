---
id: TASK-004
title: Implement or remove the general.log_level configuration
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:25'
updated_date: '2026-09-07 09:18'
labels:
  - code-review
dependencies: []
references:
  - pdf_signoff/default_config.yaml
  - pdf_signoff/cli.py
documentation:
  - docs/pdf-sign-implementation-spec.md
modified_files:
  - pdf_signoff/cli.py
  - pdf_signoff/server.py
  - tests/test_cli.py
  - tests/test_review_lifecycle.py
  - tests/test_crypto.py
  - README.md
  - docs/pdf-sign-implementation-spec.md
priority: medium
type: bug
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Specification section 21 requires Python `logging` directed to stderr, the bundled `default_config.yaml` exposes `general.log_level` with a DEBUG..CRITICAL schema, and the README documents `--general--log-level DEBUG` as a worked example. No code reads that value. All diagnostics go through `click.echo(..., err=True)` at fixed verbosity, and the only `logging` call in the package is a hard-coded error in `ReviewServer.stop`.

Setting the option therefore validates, changes the config object, and does nothing observable. That is worse than not offering it, because an operator debugging a failed signing run will reach for it first.

Decide one way: either wire the configured level into a real logging setup, or drop the option from the schema, the README, and the spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Either `general.log_level` measurably changes stderr verbosity, or the option is removed from `default_config.yaml`, the README, and the spec
- [x] #2 If implemented, DEBUG never emits the session token, the PKCS#12 password, or private-key material
- [x] #3 If implemented, stdout still carries exactly one profile JSON document and nothing else
- [x] #4 A test asserts the chosen behaviour rather than only asserting the config value round-trips
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Configure a temporary `pdf_signoff` package logger from `general.log_level` for each CLI invocation, with a stderr-only message formatter and restoration afterward.
2. Route application status and warning diagnostics through Python logging, add a secret-free DEBUG workflow message, and pass the configured level into Uvicorn while keeping access logging disabled.
3. Add CLI and review tests proving level-dependent stderr, exact single-document stdout, and absence of review or L1 secrets at DEBUG.
4. Run focused tests and the full tox suite, then record verification for human review.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation (2026-09-07): `general.log_level` is validated and documented but unread. CLI status/warning messages use `click.echo(..., err=True)` and `ReviewServer.stop` is the only package logger call. Uvicorn has a stderr handler at a fixed INFO level with access logging explicitly disabled. Implementing rather than removing the option preserves the documented operator contract and specification section 21. The logging context must restore logger state because test and embedding processes can invoke the Click command repeatedly; DEBUG messages must contain only non-secret workflow metadata, never config mappings, browser URLs, credentials, or exception chains.

Implemented invocation-scoped package logging at the validated configured threshold and restored prior logger handlers, level, and propagation afterward. CLI informational and warning diagnostics now use Python logging; the sole stdout write remains profile serialization. ReviewServer passes the same threshold to Uvicorn while retaining disabled access logs. README and specification now state the level behavior and prohibit token logging at every verbosity.

Verification: `uv run tox` passed on the final tree. Ruff lint and format checks passed; mypy passed for all 10 source files; 222 tests passed with 100% `pdf_signoff` coverage. CLI tests compare DEBUG and WARNING stderr while asserting identical single-document stdout. A real DEBUG review lifecycle verifies the bootstrap token is absent from stderr, and DEBUG L1 failure tests verify password, credential path, and private-operation details remain absent. The only warning is the existing Starlette anyio alias deprecation.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-07 09:07
---
**Agent:** Implementation and verification are complete. Task is ready for human review; it remains In Progress because this project has no review status and only the human may accept completion.
---

author: @human
created: 2026-09-07 09:18
---
**Human:** Reviewed and tested the implementation and approved closing TASK-004.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented `general.log_level` as an effective stderr verbosity control. Each CLI invocation temporarily configures the `pdf_signoff` logger, routes status and warning diagnostics through Python logging, emits a secret-free workflow message at DEBUG, and applies the selected threshold to Uvicorn without enabling access logs. Logger state is restored after the invocation, preserving repeated-call and embedding behavior. Updated README/spec logging guarantees and strengthened CLI, real review-session, and L1 secret-safety tests. Verified with `uv run tox`: 222 tests passed at 100% coverage, with Ruff and mypy clean. No known limitations, follow-up tasks, or ADR changes.
<!-- SECTION:FINAL_SUMMARY:END -->
