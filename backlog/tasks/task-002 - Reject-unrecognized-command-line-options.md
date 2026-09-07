---
id: TASK-002
title: Reject unrecognized command-line options
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:24'
updated_date: '2026-09-07 08:45'
labels:
  - code-review
dependencies: []
references:
  - pdf_signoff/cli.py
  - pdf_signoff/config.py
modified_files:
  - pdf_signoff/config.py
  - pdf_signoff/cli.py
  - tests/test_config.py
  - tests/test_cli.py
priority: high
type: bug
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Click command sets `ignore_unknown_options` and `allow_extra_args` so that Onacol can consume nested config options such as `--general--log-level`. The side effect is that any token Onacol does not recognise is discarded without a diagnostic.

Verified on the current tree: `pdf-signoff INPUT --signature SIG --autoo --no-such-flag --output OUT` exits neither with an error nor a warning. Because `--autoo` never sets `automatic`, the invocation silently falls back to interactive review mode and blocks in `session.wait_for_result()` until killed.

This matters because the CLI is the product API for unattended agent workflows. A single mistyped character turns a headless signing run into a process that hangs forever holding a loopback server open, with no signal that anything is wrong.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A mistyped or unknown option such as `--autoo` or `--no-such-flag` exits non-zero with a UsageError naming the offending token
- [x] #2 Legitimate nested Onacol options such as `--general--log-level DEBUG` and `--output-suffix _approved` still work unchanged
- [x] #3 Leftover args are checked against the Onacol schema before any PDF inspection or output resolution runs
- [x] #4 Tests cover an unknown flag, a near-miss of `--auto`, and a valid nested Onacol option
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Characterize how Onacol parses schema-backed CLI overrides and identify discarded tokens.
2. Reject any forwarded token not consumed as a valid schema option/value before returning loaded configuration.
3. Add CLI and configuration tests for unknown options, the --auto near-miss, valid nested options, and early rejection.
4. Run focused and full project verification, then prepare the task for human review.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Onacol 0.3.5 config_from_cli_args scans every -- token, applies only names present in its flattened schema, and silently ignores all other tokens. ConfigManager.get_cli_opt_conf_value is the public schema-backed lookup suitable for validating forwarded Click args before applying them.

Implemented schema-backed validation of all Click-forwarded CLI tokens before Onacol applies overrides. Unknown options and malformed option/value pairs now raise CliConfigArgumentError, which the command presents as a Click UsageError before output resolution or PDF inspection.

Verification: uv run tox passed. Ruff lint and format passed; mypy passed for all 10 source files; 219 tests passed with 100% pdf_signoff coverage. The only emitted warning is an existing Starlette anyio alias deprecation.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-07 08:40
---
**Agent:** Implementation and verification are complete. Task is ready for human review; it remains In Progress because this project has no review status and only the human may accept completion.
---

author: @human
created: 2026-09-07 08:45
---
**Human:** Accepted the completed implementation and requested that task 002 be closed.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added strict validation for Click-forwarded Onacol arguments using ConfigManager's public schema lookup. Unknown options such as --autoo and --no-such-flag now exit with a UsageError naming the token, while valid nested overrides retain their existing behavior. Added configuration-boundary and CLI regression tests, including proof that rejection precedes output and PDF processing. Verified with uv run tox: 219 tests passed at 100% coverage, with Ruff and mypy clean. No known implementation limitations, follow-up tasks, or ADR changes.
<!-- SECTION:FINAL_SUMMARY:END -->
