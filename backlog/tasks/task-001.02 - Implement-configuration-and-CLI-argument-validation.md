---
id: TASK-001.02
title: Implement configuration and CLI argument validation
status: To Do
assignee: []
created_date: '2026-09-04 18:02'
updated_date: '2026-09-04 18:38'
labels: []
dependencies:
  - TASK-001.01
references:
  - docs/pdf-sign-implementation-spec.md#4-user-visible-cli-contract
  - docs/pdf-sign-implementation-spec.md#7-configuration
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
- [ ] #1 The Click CLI accepts the required input PDF and `--signature`, plus `--coords`, `--output`, `--review`, `--auto`, `--level`, `--overwrite`, `--allow-signed-input`, and `--config`
- [ ] #2 Review is the default mode, `--review` and `--auto` are mutually exclusive, and auto mode is rejected unless `--coords` is supplied
- [ ] #3 Onacol layers the bundled YAML defaults/schema, discovered or explicit user YAML, environment overrides, and nested CLI overrides with documented precedence, then validates the merged configuration
- [ ] #4 The existing config-template capability remains available; configured filesystem paths expand environment variables and `~`, port zero is accepted, and invalid level or configuration values fail clearly
- [ ] #5 Tests cover defaults, config precedence, XDG/home discovery, path expansion, environment and CLI overrides, template generation, and mode validation
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Agent
created: 2026-09-04 18:38
---
Updated the task to extend the existing Click/Onacol scaffold. This replaces the draft argparse/tomllib assumption with Onacol’s YAML-first layered configuration model while retaining the required behavioral precedence.
---
<!-- COMMENTS:END -->
