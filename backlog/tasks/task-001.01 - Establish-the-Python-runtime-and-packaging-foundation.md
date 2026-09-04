---
id: TASK-001.01
title: Extend the existing Python runtime and packaging scaffold
status: To Do
assignee: []
created_date: '2026-09-04 18:02'
updated_date: '2026-09-04 18:38'
labels: []
dependencies: []
references:
  - docs/pdf-sign-implementation-spec.md#2-technology-stack
  - docs/pdf-sign-implementation-spec.md#19-suggested-repository-structure
parent_task_id: TASK-001
priority: high
type: chore
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The checked-in project is the intentional starting scaffold for the PDF Signoff product. Extend its Python 3.13 package, Click entry point, and Onacol configuration foundation with the reproducible dependencies and module structure needed by the backend and frontend work; do not replace those established choices merely to mirror the earlier implementation-spec draft.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The project installs on Python 3.13 and exposes the `pdf-signoff` console command
- [ ] #2 The existing Click command and Onacol ConfigManager integration remain the CLI and configuration foundation
- [ ] #3 FastAPI, Uvicorn, PyMuPDF, pyHanko, Pydantic v2, and development test dependencies are declared at tested versions in the lockfile
- [ ] #4 The source and test layout supports distinct configuration, profile, geometry, inspection, stamping, crypto, output, and server modules without retaining starter placeholder behavior
- [ ] #5 A clean environment can install the locked project and invoke `pdf-signoff --help` successfully
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Human
created: 2026-09-04 18:38
---
The existing project is intentional initial scaffolding. Preserve its Click and Onacol setup, and use the renamed product/CLI name `pdf-signoff`.
---
<!-- COMMENTS:END -->
