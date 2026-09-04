---
id: TASK-001.02
title: Implement configuration and CLI argument validation
status: In Progress
assignee:
  - '@opencode'
created_date: '2026-09-04 18:02'
updated_date: '2026-09-04 19:18'
labels: []
dependencies:
  - TASK-001.01
references:
  - docs/pdf-sign-implementation-spec.md#4-user-visible-cli-contract
  - docs/pdf-sign-implementation-spec.md#7-configuration
modified_files:
  - pdf_signoff/cli.py
  - pdf_signoff/config.py
  - pdf_signoff/default_config.yaml
  - tests/test_cli.py
  - tests/test_config.py
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Agents and humans need one stable Click command whose mode selection is explicit and whose defaults can be configured without contaminating machine-readable output. Extend the scaffold’s Onacol-based layered configuration and validate invocations before PDF mutation begins.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The Click CLI accepts the required input PDF and `--signature`, plus `--coords`, `--output`, `--review`, `--auto`, `--level`, `--overwrite`, `--allow-signed-input`, and `--config`
- [x] #2 Review is the default mode, `--review` and `--auto` are mutually exclusive, and auto mode is rejected unless `--coords` is supplied
- [x] #3 Onacol layers the bundled YAML defaults/schema, discovered or explicit user YAML, environment overrides, and nested CLI overrides with documented precedence, then validates the merged configuration
- [x] #4 The existing config-template capability remains available; configured filesystem paths expand environment variables and `~`, port zero is accepted, and invalid level or configuration values fail clearly
- [x] #5 Tests cover defaults, config precedence, XDG/home discovery, path expansion, environment and CLI overrides, template generation, and mode validation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Define the complete schema-backed YAML defaults and a configuration loader that chooses explicit YAML over discovered XDG/home YAML, then applies environment and Onacol nested CLI layers before validation and path expansion. 2. Extend the existing Click command with required PDF/signature paths, signing options, explicit review/auto validation, and an immutable invocation handoff while keeping config-template generation standalone and stdout silent. 3. Add focused tests for all configuration layers, discovery, expansion, validation, template output, command options, mode rules, and the no-PDF-operation handoff. 4. Run the focused and full test suites with coverage, Ruff lint/format, mypy, tox, lock checks, and installed CLI smoke checks; record evidence and leave the task In Progress for human acceptance.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation found TASK-001.01 already provided the Python 3.13 Click/Onacol scaffold, but only general.log_level existed and no signing arguments were validated. Implemented discovery at `$XDG_CONFIG_HOME/pdf-signoff/config.yaml` with fallback to `~/.config/pdf-signoff/config.yaml`; explicit `--config` replaces discovery. ConfigManager loads bundled defaults/schema, the selected user YAML, environment values, and nested CLI values before validation. Onacol appends an underscore to env_var_prefix, so the manager uses `PDF_SIGNOFF_` to expose the documented `PDF_SIGNOFF__...` environment names. The immutable Invocation return value carries the same ConfigManager config reference and validated CLI values without executing later PDF behavior or writing stdout. Configured `l1.pkcs12_path` expands environment variables and `~` after merging and validation. Verification: focused tests 27 passed; full suite 43 passed with 100% coverage on Python 3.13.15; Ruff lint and format checks passed; mypy passed for 10 source files; `uv lock --check` resolved 61 packages; tox lint and py313 environments passed; `uv build` produced the sdist and wheel. A fresh temporary environment installed the wheel, loaded the bundled YAML, displayed `pdf-signoff --help`, and completed a validation-only command with empty stdout. The real CLI also rejected `--auto` without `--coords` on stderr. No dependency changes, ADRs, blockers, or follow-up tasks.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Agent
created: 2026-09-04 18:38
---
Updated the task to extend the existing Click/Onacol scaffold. This replaces the draft argparse/tomllib assumption with Onacol’s YAML-first layered configuration model while retaining the required behavioral precedence.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Extended the preserved Click/Onacol scaffold with the complete `pdf-signoff` argument contract, explicit review/auto validation, a silent immutable invocation handoff, schema-backed product defaults, deterministic explicit/XDG/home YAML selection, environment and nested CLI precedence, merged-config validation, and configured path expansion. Config-template generation remains available without signing arguments, port zero is valid, and all human-readable failures stay off stdout. Verified with 27 focused tests and 43 full-suite tests at 100% coverage, passing Ruff format/lint, mypy, lock check, both tox environments, package build, current CLI checks, and a fresh wheel-install CLI smoke test. PDF inspection, output, stamping, review server, and cryptographic behavior remain intentionally deferred to later subtasks. No known blockers, ADRs, dependency changes, or follow-up tasks.
<!-- SECTION:FINAL_SUMMARY:END -->
