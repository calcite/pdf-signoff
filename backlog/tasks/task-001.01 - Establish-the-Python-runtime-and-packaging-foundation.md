---
id: TASK-001.01
title: Extend the existing Python runtime and packaging scaffold
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:02'
updated_date: '2026-09-07 07:11'
labels: []
dependencies: []
references:
  - docs/pdf-sign-implementation-spec.md#2-technology-stack
  - docs/pdf-sign-implementation-spec.md#19-suggested-repository-structure
modified_files:
  - pyproject.toml
  - uv.lock
  - pdf_signoff/cli.py
  - pdf_signoff/default_config.yaml
  - pdf_signoff/pdf_signoff.py
  - pdf_signoff/config.py
  - pdf_signoff/profile.py
  - pdf_signoff/geometry.py
  - pdf_signoff/inspection.py
  - pdf_signoff/stamping.py
  - pdf_signoff/crypto.py
  - pdf_signoff/output.py
  - pdf_signoff/server.py
  - tests/test_pdf_signoff.py
  - tests/test_cli.py
  - tests/test_package_foundation.py
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
- [x] #1 The project installs on Python 3.13 and exposes the `pdf-signoff` console command
- [x] #2 The existing Click command and Onacol ConfigManager integration remain the CLI and configuration foundation
- [x] #3 FastAPI, Uvicorn, PyMuPDF, pyHanko, Pydantic v2, and development test dependencies are declared at tested versions in the lockfile
- [x] #4 The source and test layout supports distinct configuration, profile, geometry, inspection, stamping, crypto, output, and server modules without retaining starter placeholder behavior
- [x] #5 A clean environment can install the locked project and invoke `pdf-signoff --help` successfully
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Update project metadata and dependency declarations for the `pdf-signoff` command and the required Python 3.13 runtime libraries, then regenerate the uv lockfile.
2. Preserve the Click/Onacol configuration-loading entry point while removing cookiecutter placeholder output and sample application code.
3. Add minimal importable module boundaries for configuration, profiles, geometry, inspection, stamping, crypto, output, and server concerns without implementing later subtasks.
4. Replace starter tests with focused foundation tests for CLI metadata/help, Onacol command settings, module imports, and required locked runtime/test distributions.
5. Verify formatting, lint, types, tests, package build, frozen clean installation, and installed `pdf-signoff --help` on Python 3.13.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation: the project already targets Python >=3.13 and uses Click plus Onacol ConfigManager in `pdf_signoff/cli.py`. The console script is incorrectly named `pdf_signoff`; the CLI and tests retain cookiecutter placeholder behavior; only `cli.py`, `pdf_signoff.py`, and `default_config.yaml` exist. `uv.lock` currently resolves the existing dev group but contains none of FastAPI, Uvicorn, PyMuPDF, pyHanko, or Pydantic. TASK-001.02 owns full configuration and argument behavior, and TASK-001.03+ own domain implementations, so this foundation will add importable module seams only.

Implemented the foundation with a normalized `pdf-signoff` distribution/console script, bounded runtime dependency declarations, schema-backed bundled YAML, and the preserved Click command plus Onacol ConfigManager loading order. Removed the cookiecutter greeting module and placeholder CLI/test behavior. Added importable `config`, `profile`, `geometry`, `inspection`, `stamping`, `crypto`, `output`, and `server` module boundaries only; their domain behavior remains intentionally assigned to later subtasks.

Verification evidence: `uv lock` resolved 61 packages; `uv sync --frozen --group dev` succeeded on Python 3.13.15; 22 pytest tests passed with 100% coverage; Ruff check/format and mypy passed; `uv run tox` passed lint and py313 environments; `uv build` produced sdist and wheel. A fresh `/tmp/opencode/pdf-signoff-clean` environment installed from the frozen lock and ran `pdf-signoff --help`; a separate fresh environment installed the built wheel, ran help and a nested Onacol override, and imported every new module.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Human
created: 2026-09-04 18:38
---
The existing project is intentional initial scaffolding. Preserve its Click and Onacol setup, and use the renamed product/CLI name `pdf-signoff`.
---

author: Human
created: 2026-09-07 07:11
---
The human reviewed the implementation and confirmed it works; accepted for completion.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Extended the intentional Python 3.13 scaffold rather than replacing it: the distribution and installed command are now `pdf-signoff`; Click still owns the entry point and Onacol ConfigManager still layers YAML, environment, and nested CLI values before validation. Added schema-backed bundled defaults, locked FastAPI/Uvicorn/PyMuPDF/pyHanko/Pydantic v2 plus existing dev tooling, established eight importable domain module boundaries, and removed cookiecutter placeholder code/tests.

Verification: `uv sync --frozen --group dev`, `uv lock --check`, 22 pytest tests with 100% coverage, Ruff lint/format, mypy, and both tox environments pass on Python 3.13.15. `uv build` produced both artifacts; separate clean environments successfully installed from the frozen lock and built wheel, invoked `pdf-signoff --help`, loaded a nested Onacol override, and imported all module boundaries.

Known limitations/follow-up: domain modules intentionally contain boundaries only; TASK-001.02 and later subtasks own CLI/config behavior and application implementations. No blockers, no ADRs, and no new follow-up tasks.
<!-- SECTION:FINAL_SUMMARY:END -->
