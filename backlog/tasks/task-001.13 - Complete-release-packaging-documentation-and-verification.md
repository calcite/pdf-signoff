---
id: TASK-001.13
title: 'Complete release packaging, documentation, and verification'
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:04'
updated_date: '2026-09-10 10:35'
labels: []
dependencies:
  - TASK-001.10
  - TASK-001.11
  - TASK-001.12
references:
  - docs/pdf-sign-implementation-spec.md#23-implementation-milestones
  - docs/pdf-sign-implementation-spec.md#24-definition-of-done
  - docs/pdf-sign-implementation-spec.md#25-explicit-non-goals-for-the-mvp
modified_files:
  - README.md
  - tests/e2e/wheel_smoke.py
  - .github/workflows/ci.yml
  - .github/workflows/release.yml
  - pyproject.toml
  - release_guide.md
  - CHANGELOG.md
  - pdf_signoff/__init__.py
  - uv.lock
parent_task_id: TASK-001
priority: medium
type: docs
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The completed subsystems must ship as one reproducible local utility with clear operational boundaries. Finish installation and usage documentation, verify built artifacts rather than only source checkouts, run the cross-cutting test matrix that demonstrates the draft definition of done, and prepare GitHub CI, tagged releases, PyPI Trusted Publishing, and operator documentation for the calcite/pdf-signoff repository.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README documentation covers installation, configuration, review, auto, output capture, overwrite, signed-input override, and L0 versus L1 semantics with executable examples
- [x] #2 Documentation states localhost and credential assumptions, unsupported input classes, agent/workflow responsibility, and all explicit MVP non-goals without overstating legal identity assurance
- [x] #3 A built wheel contains the production frontend and all required package data, and `pdf-signoff` review and auto smoke tests pass from an isolated installation without Node.js
- [x] #4 The Python unit/integration suite, Vitest suite, and Playwright workflow pass together on Python 3.13 using locked dependencies
- [x] #5 Release verification demonstrates all top-level definition-of-done behaviors, including stdout isolation, deterministic safe outputs, geometry edge cases, review edits, L1 integrity, signed-input protection, and loopback session security
- [x] #6 GitHub CI validates locked Python and frontend dependencies, quality checks, tests, frontend production build, and distribution metadata on pushes and pull requests targeting either master or main.
- [x] #7 A tag-driven release workflow verifies vX.Y.Z against pyproject.toml, builds and smoke-tests artifacts, publishes with PyPI Trusted Publishing, and creates a GitHub Release with those artifacts.
- [x] #8 release_guide.md documents first push and master/main handling, GitHub and PyPI Trusted Publishing setup, routine versioned release steps, and recovery for already-published PyPI versions.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect Python/frontend packaging, release requirements, and supplied workflow examples; retain checks that apply to pdf-signoff.
2. Add CI for master/main pushes and pull requests using locked dependencies, quality checks, tests, frontend builds, and distribution metadata validation.
3. Add tag/manual release automation that validates the tag/package version, smoke-tests artifacts, publishes via OIDC, and creates a GitHub Release.
4. Correct repository metadata and document branch setup, Trusted Publishing, normal releases, and recovery in release_guide.md.
5. Verify workflow YAML and release-equivalent project checks, then record evidence for review.
6. Maintain final package metadata, lockfile, and changelog entries for each requested release version; verify the installed distribution metadata.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial release investigation (2026-09-04): all twelve functional subtasks remain In Progress but have checked acceptance criteria and detailed verification evidence. The current source has 213 Python tests with a configured 100% coverage threshold, 12 Vitest cases, and 2 real Chromium Playwright workflows. Build tooling is Hatch via `uv build`; Vite writes hashed production assets directly to `pdf_signoff/web_dist`; Hatch currently recurses the selected `pdf_signoff` package. The starter README does not document product operation. Actual behavior is a Python >=3.13 `pdf-signoff` Click command using Onacol schema-backed YAML: bundled defaults, explicit YAML or XDG/home discovery, `PDF_SIGNOFF__...` environment values, then nested unknown Click arguments. Review is default; auto requires `--coords`; output is transactional and separate; L1 loads an expanded `.p12`/`.pfx`, reads its password from the configured environment or secure TTY prompt, and provides revision integrity without trust or identity assurance. Existing review security is one-shot loopback HTTP with a 256-bit URL bootstrap token, HttpOnly SameSite=Strict cookie or bearer credential, same-origin checks, no CORS/generic file APIs/access logging, and fixed selected resources. The loopback HTTP cookie is intentionally not Secure. The old implementation specification still contains pre-scaffold `pdf-sign`/TOML assumptions, so release documentation must explicitly follow actual Click/Onacol behavior rather than repeat those obsolete draft examples.

Implementation and release checkpoint (2026-09-04): replaced the scaffold README with the actual installed product contract: Python 3.13 installation; default review and explicit auto workflows; final-profile capture; normalized profile rules; deterministic output, transactional overwrite, and process streams; the generated Onacol YAML defaults and exact default/user/environment/nested-CLI precedence; L0 visual-only and L1 invisible integrity semantics and PKCS#12 secret handling; signed-input refusal/override; local-session assumptions; rejected inputs; all explicit MVP non-goals; and the external agent/workflow authorization boundary. Extended `tests/e2e/wheel_smoke.py` into a reusable real release smoke covering installed auto/review, output collision and overwrite, live loopback auth/origin/generic-path security, token-log isolation, generated self-signed L1 intact/valid/untrusted validation, and signed-input refusal/override while proving Node is absent from PATH.

Package evidence: `uv build` succeeded for sdist and wheel. Final wheel SHA-256 is `affc414789761c05c4c2a59bce7fce284104155a1aa6e67d639eee0c0f1addbd`; sdist SHA-256 is `842fd6693fe3d8edabcaa930d44fb2127ae758f64dc550f7e20b680ad6e36b3d`. Wheel inspection lists `default_config.yaml`, all Python runtime modules, `web_dist/index.html`, hashed CSS/application JS, and the PDF.js worker. Hatch package recursion is sufficient, so no redundant package-data declaration was added. A fresh Python 3.13.15 venv installed the final wheel and 38 runtime distributions, and installed help/config-template plus the expanded smoke all passed with PATH restricted to the venv.

Release checks passed: `uv sync --frozen --group dev` (63 packages checked); `uv lock --check` (65 packages resolved); source pytest 213/213 with 739/739 statements and 100.00% coverage; Ruff lint and 24-file format check; mypy for 10 production modules and separately the release smoke (11 files together); tox lint and py313 environments, with py313 repeating 213 tests at 100%; `npm ci` (97 packages audited), `npm audit` (0 vulnerabilities), Vue typecheck, Vitest 12/12 in 4 files, Vite production build (4 packaged artifacts), and Playwright Chromium 2/2; `git diff --check`; two successful `uv build` runs; final wheel manifest/help/template checks; and the real isolated-wheel release smoke. Full automated coverage includes stdout isolation, deterministic/multi-dot/configured/explicit outputs, transactional overwrite and failure cleanup, all required geometry rotations/CropBoxes/origins/page sizes, review preload/edit/remove/replace/save/no-download behavior, L0 rendering/transparency, L1 whole-revision integrity and tamper detection, signed-input protection across supported modes, and one-shot loopback session/API security. The only warning is the existing upstream Starlette AnyIO `BlockingPortal` deprecation warning. No release blocker, functional correction, dependency change, ADR, or follow-up task was found.

Final artifact clarification: a wording-only README correction changed distribution metadata after the first recorded checksum. The final rebuilt artifacts supersede the earlier hashes: wheel SHA-256 `87712536713280ba182679b1c0d3ff1018449baf3812973556ac7ffffc3161e9`; sdist SHA-256 `7625450908c4be5e00097fc94a140080faa4905d6c8ce262fc26490666b6e137`. The final wheel was installed into another fresh Python 3.13.15 venv and the complete Node-free auto/review/L1/security/signature-guard smoke passed again.

Deployment automation checkpoint (2026-09-06): added `.github/workflows/ci.yml` for pushes and pull requests on both `master` and `main`, plus manual runs. It installs Python 3.13 with uv and locked dependencies, runs lock/Ruff/mypy/pytest checks, installs locked Node dependencies, validates typecheck/Vitest/Playwright, rebuilds the tracked web distribution, and checks wheel/sdist metadata. Added `.github/workflows/release.yml` for `vX.Y.Z` tags and manual recovery runs. It requires an exact pyproject-version match, repeats release checks, performs an isolated Node-free installed-wheel smoke, sends artifacts through the workflow, publishes only through the `pypi` OIDC environment, then attaches the artifacts to a generated GitHub Release. Manual `skip_pypi` is limited to an already-published version. Corrected PyPI metadata links to `calcite/pdf-signoff` and added `release_guide.md` covering initial master/main choice, remote setup, GitHub permissions/environment, PyPI pending Trusted Publisher setup, routine releases, and recovery.

Verification (2026-09-06): workflow YAML parsed with PyYAML and `git diff --check` passed. `uv sync --locked --group dev`, `uv lock --check`, Ruff lint/format, mypy, and pytest all passed (213 tests, 100.00% coverage). `npm ci`, audit (0 vulnerabilities), typecheck, Vitest (16 tests), production build with tracked-assets diff check, and Playwright (2 tests) passed. `uv build`, `twine check`, and the full isolated wheel auto/review/L1/security/signed-input smoke passed without Node on PATH. The sandbox has no GitHub credentials or actionlint binary, so workflows have not run remotely; the guide records the required human GitHub/PyPI setup.

Release preparation investigation (2026-09-08): the source and lockfile currently identify the package as 0.1.0, while CHANGELOG.md prematurely calls that version the first PyPI release. The requested initial release is v0.1.1, so the release entry will be corrected rather than retaining a false 0.1.0 publication history.

Initial-release metadata update (2026-09-08): changed CHANGELOG.md to the sole `0.1.1 (2026-09-08)` initial-release entry; synchronized `pyproject.toml`, `pdf_signoff.__version__`, and the editable local-package entry in `uv.lock`. `uv lock --check` and `uv build` passed. Wheel and sdist PKG-INFO metadata both report 0.1.1. `uv run pdf-signoff --version` prints `pdf-signoff, version 0.1.1`; targeted package/CLI tests passed (43 tests).

Release metadata update (2026-09-10): synchronized pyproject.toml, pdf_signoff.__version__, and uv.lock to 0.1.2; converted the existing changelog notes into the dated 0.1.2 release entry. Verification passed: uv lock --check and uv run pytest tests/test_cli.py tests/test_package_foundation.py (43 passed).
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @human
created: 2026-09-04 20:54
---
The human requested implementation and release verification of TASK-001.13 only, with all functional subtasks left In Progress pending human acceptance.
---

author: @opencode
created: 2026-09-06 07:49
---
Agent: CI/release automation and the deployment guide are ready for human review. Remote GitHub and PyPI execution is pending repository push plus the documented Trusted Publisher configuration.
---

author: @human
created: 2026-09-08 13:39
---
Human: Requested the first release as v0.1.1, with an initial-release changelog and matching version bumps in relevant files.
---

author: @opencode
created: 2026-09-08 13:39
---
Agent: v0.1.1 release metadata and the initial changelog entry are ready for review. Local lock, build, package metadata, CLI-version, and targeted test checks passed; publication remains the tag-driven GitHub/PyPI workflow.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed release documentation, packaging verification, and deployment automation without changing product behavior. README documents the installed Python 3.13 CLI, Onacol configuration, review/auto/output workflows, L0/L1 and PKCS#12 handling, loopback security, rejected inputs, MVP non-goals, and external agent/workflow responsibilities. The project includes CI for master/main pushes and pull requests, plus tag/manual release automation that validates matching versions, smoke-tests artifacts, publishes via PyPI Trusted Publishing OIDC, and creates GitHub Releases. release_guide.md documents setup, routine releases, and recovery.

Verified the release-equivalent suite: 213 Python tests at 100% coverage, Ruff, mypy, tox, locked dependency checks, frontend typecheck/Vitest/production build/Playwright, distribution builds and metadata checks, and a Node-free isolated wheel smoke covering auto, review, L1, session security, and signed-input protection. The requested release metadata now reports v0.1.2 in package sources and uv.lock, with a dated changelog entry; uv lock --check and 43 focused CLI/package-foundation tests passed.

Known limitations: remote GitHub/PyPI workflow execution still requires repository push and human-managed Trusted Publisher setup; an upstream Starlette AnyIO BlockingPortal deprecation warning remains. No ADRs or follow-up tasks were needed.
<!-- SECTION:FINAL_SUMMARY:END -->
