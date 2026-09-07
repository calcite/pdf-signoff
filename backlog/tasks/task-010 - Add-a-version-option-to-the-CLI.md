---
id: TASK-010
title: Add a --version option to the CLI
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:26'
updated_date: '2026-09-07 13:32'
labels:
  - code-review
dependencies: []
references:
  - pdf_signoff/cli.py
  - pdf_signoff/__init__.py
priority: low
type: enhancement
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The published console script has no `--version`. `pdf_signoff.__version__` exists and the package is on PyPI, but there is no way to ask an installed binary what it is.

Every emitted placement profile and every signed PDF is the output of a specific build, and the stated audience is agents capturing that output into a workflow. Recording which version produced a profile currently requires inspecting the Python environment rather than asking the tool.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `pdf-signoff --version` prints the version and exits zero without requiring INPUT_PDF or --signature
- [x] #2 The reported version comes from installed package metadata rather than a second hard-coded literal
- [x] #3 The option is eager, so it works alongside the existing `--get-config-template` behaviour
- [x] #4 A test asserts the printed version matches the package metadata
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Resolve the distribution version through installed package metadata and expose it through an eager Click --version option.
2. Add CLI coverage proving --version bypasses required signing inputs and matches package metadata.
3. Run the focused CLI tests and record verification results.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation: cli.main is a Click command; --get-config-template is the existing eager option. Click's version_option can resolve the installed pdf-signoff distribution metadata directly, avoiding another version literal. Focused coverage belongs in tests/test_cli.py.

Verification passed: uv run pdf-signoff --version printed 'pdf-signoff, version 0.1.0' with exit zero; uv run pytest tests/test_cli.py passed (26 tests); uv run pytest passed (228 tests, 1 pre-existing third-party deprecation warning); uv run ruff check . passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added Click's eager metadata-backed --version option for the pdf-signoff console command. The CLI test checks its output against importlib.metadata.version('pdf-signoff') without signing inputs. Verified with the installed console command, focused and full pytest suites, and Ruff. No follow-up tasks or ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
