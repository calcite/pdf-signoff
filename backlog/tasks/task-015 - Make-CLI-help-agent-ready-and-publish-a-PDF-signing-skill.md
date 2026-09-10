---
id: TASK-015
title: Make CLI help agent-ready and publish a PDF signing skill
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-09 08:15'
updated_date: '2026-09-10 10:34'
labels: []
dependencies: []
references:
  - README.md
  - 'https://agentskills.io/specification'
modified_files:
  - pdf_signoff/cli.py
  - tests/test_cli.py
  - skills/pdf-signoff/SKILL.md
  - README.md
  - CHANGELOG.md
priority: medium
type: docs
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The released CLI is documented thoroughly in the README, but its runtime help omits the stream contract, safe-output behavior, hidden Onacol overrides, profile semantics, and trust boundaries that an autonomous agent needs. Publish a portable Agent Skills workflow that treats current help as the source of truth and handles signing results conservatively.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Installed `pdf-signoff --help` is self-contained enough to select a mode, configure an invocation, predict safe outputs, and interpret success or failure
- [x] #2 Help documents all supported nested configuration overrides, discovery and precedence, and current defaults
- [x] #3 A standards-compliant portable skill at `skills/pdf-signoff/SKILL.md` guides agents through authorization, invocation, output validation, failure recovery, review, and L1 secret/trust handling
- [x] #4 README links the portable skill and accurately describes stderr behavior at configurable log levels
- [x] #5 Automated tests protect the expanded help contract and relevant project checks pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Expand Click help with concise mode, output, stream, profile, level, configuration, and example sections. 2. Add the portable Agent Skills file centered on runtime help and conservative output handling. 3. Link the skill and correct stderr wording in README; record the change in the changelog. 4. Add help-contract tests and verify the skill, source suite, and installed artifact.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented an expanded Click epilog that keeps the ordinary option table concise while documenting review/auto selection, transactional outputs, stdout/stderr behavior, profile semantics, L0/L1 limits, signed-input risk, all ten Onacol nested overrides and defaults, and examples. Added the portable Agent Skills artifact at skills/pdf-signoff/SKILL.md; it uses installed --help as source of truth and adds conservative authorization, temporary stdout capture, success validation, recovery, review, credential, and trust guidance. README now links the skill and accurately qualifies INFO-level output-path diagnostics; CHANGELOG has an Unreleased entry.

Verification: focused CLI tests 26/26; full suite 230/230 with 826/826 statements and 100% coverage; Ruff lint and 24-file format check; mypy for 10 source files; git diff check; official skills-ref validation; source/wheel build; source distribution contains the complete skill directory; and a fresh Python 3.13 wheel installation displayed the complete revised help. The sole warning is the existing upstream Starlette AnyIO BlockingPortal deprecation.

Release metadata correction (2026-09-10): the changelog notes now form the dated 0.1.2 release entry; package metadata and uv.lock also report 0.1.2. Verification passed: uv lock --check and uv run pytest tests/test_cli.py tests/test_package_foundation.py (43 passed).
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-09 08:23
---
Agent: Implementation and verification are complete. The project has no configured review status, so TASK-015 remains In Progress for human acceptance.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Expanded pdf-signoff --help into a concise standalone operating contract covering modes, output safety and streams, profile semantics, L0/L1 limits, signed-input handling, nested configuration overrides/defaults, and examples. Added the validated portable skills/pdf-signoff/SKILL.md, centered on live help plus conservative authorization, capture, validation, failure, review, credential, and trust procedures. Linked it from README, corrected configurable stderr semantics, added help-contract tests, and recorded the work in the dated 0.1.2 changelog entry.

Verified with 26 focused CLI tests; 230 full tests and 100% coverage; Ruff, format, mypy, and diff checks; official agentskills validation; source/wheel builds with the skill in the sdist; revised help from a fresh wheel installation; and, after the release version update, uv lock --check plus 43 CLI/package-foundation tests. Known limitation: the existing upstream Starlette AnyIO deprecation warning remains. No ADR or follow-up task was needed.
<!-- SECTION:FINAL_SUMMARY:END -->
