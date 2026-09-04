---
id: TASK-001.13
title: 'Complete release packaging, documentation, and verification'
status: In Progress
assignee:
  - '@opencode'
created_date: '2026-09-04 18:04'
updated_date: '2026-09-04 21:04'
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
parent_task_id: TASK-001
priority: medium
type: docs
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The completed subsystems must ship as one reproducible local utility with clear operational boundaries. Finish installation and usage documentation, verify built artifacts rather than only source checkouts, and run the cross-cutting test matrix that demonstrates the draft definition of done.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README documentation covers installation, configuration, review, auto, output capture, overwrite, signed-input override, and L0 versus L1 semantics with executable examples
- [x] #2 Documentation states localhost and credential assumptions, unsupported input classes, agent/workflow responsibility, and all explicit MVP non-goals without overstating legal identity assurance
- [x] #3 A built wheel contains the production frontend and all required package data, and `pdf-signoff` review and auto smoke tests pass from an isolated installation without Node.js
- [x] #4 The Python unit/integration suite, Vitest suite, and Playwright workflow pass together on Python 3.13 using locked dependencies
- [x] #5 Release verification demonstrates all top-level definition-of-done behaviors, including stdout isolation, deterministic safe outputs, geometry edge cases, review edits, L1 integrity, signed-input protection, and loopback session security
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Replace the scaffold README with the actual Python 3.13 installation and `pdf-signoff` Click contract, executable review/auto/output/profile examples, schema-free Onacol YAML configuration template and precedence, overwrite and signed-input safeguards, and accurate L0/L1 credential and integrity semantics.
2. Document the local security and operating model, supported and rejected inputs, complete MVP non-goals, the agent/workflow responsibility boundary, process/stdout/stderr behavior, and known trust/legal limitations without broadening product claims.
3. Rebuild from locked dependencies and inspect sdist/wheel contents; adjust Hatch package-data declarations only if needed so `default_config.yaml` and the complete production `web_dist` ship reproducibly.
4. Run the comprehensive Python 3.13 and frontend release matrix: frozen sync/lock, pytest at the configured 100% coverage threshold, Ruff, mypy, tox, npm clean-install/audit/typecheck/Vitest/build, Playwright Chromium E2E, build/diff checks, and package content inspection.
5. Install the built wheel into an isolated environment with Node absent from PATH and run help/config-template plus real auto, review, L1, signed-input guard, output/overwrite/stdout-isolation, and loopback/session-security smokes; correct only release-level defects within the parent definition of done and update any affected prior task notes.
6. Read the finalization guide, re-read TASK-001.13, check criteria only against recorded evidence, add modified files/notes/final summary, and leave the task In Progress for human acceptance.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial release investigation (2026-09-04): all twelve functional subtasks remain In Progress but have checked acceptance criteria and detailed verification evidence. The current source has 213 Python tests with a configured 100% coverage threshold, 12 Vitest cases, and 2 real Chromium Playwright workflows. Build tooling is Hatch via `uv build`; Vite writes hashed production assets directly to `pdf_signoff/web_dist`; Hatch currently recurses the selected `pdf_signoff` package. The starter README does not document product operation. Actual behavior is a Python >=3.13 `pdf-signoff` Click command using Onacol schema-backed YAML: bundled defaults, explicit YAML or XDG/home discovery, `PDF_SIGNOFF__...` environment values, then nested unknown Click arguments. Review is default; auto requires `--coords`; output is transactional and separate; L1 loads an expanded `.p12`/`.pfx`, reads its password from the configured environment or secure TTY prompt, and provides revision integrity without trust or identity assurance. Existing review security is one-shot loopback HTTP with a 256-bit URL bootstrap token, HttpOnly SameSite=Strict cookie or bearer credential, same-origin checks, no CORS/generic file APIs/access logging, and fixed selected resources. The loopback HTTP cookie is intentionally not Secure. The old implementation specification still contains pre-scaffold `pdf-sign`/TOML assumptions, so release documentation must explicitly follow actual Click/Onacol behavior rather than repeat those obsolete draft examples.

Implementation and release checkpoint (2026-09-04): replaced the scaffold README with the actual installed product contract: Python 3.13 installation; default review and explicit auto workflows; final-profile capture; normalized profile rules; deterministic output, transactional overwrite, and process streams; the generated Onacol YAML defaults and exact default/user/environment/nested-CLI precedence; L0 visual-only and L1 invisible integrity semantics and PKCS#12 secret handling; signed-input refusal/override; local-session assumptions; rejected inputs; all explicit MVP non-goals; and the external agent/workflow authorization boundary. Extended `tests/e2e/wheel_smoke.py` into a reusable real release smoke covering installed auto/review, output collision and overwrite, live loopback auth/origin/generic-path security, token-log isolation, generated self-signed L1 intact/valid/untrusted validation, and signed-input refusal/override while proving Node is absent from PATH.

Package evidence: `uv build` succeeded for sdist and wheel. Final wheel SHA-256 is `affc414789761c05c4c2a59bce7fce284104155a1aa6e67d639eee0c0f1addbd`; sdist SHA-256 is `842fd6693fe3d8edabcaa930d44fb2127ae758f64dc550f7e20b680ad6e36b3d`. Wheel inspection lists `default_config.yaml`, all Python runtime modules, `web_dist/index.html`, hashed CSS/application JS, and the PDF.js worker. Hatch package recursion is sufficient, so no redundant package-data declaration was added. A fresh Python 3.13.15 venv installed the final wheel and 38 runtime distributions, and installed help/config-template plus the expanded smoke all passed with PATH restricted to the venv.

Release checks passed: `uv sync --frozen --group dev` (63 packages checked); `uv lock --check` (65 packages resolved); source pytest 213/213 with 739/739 statements and 100.00% coverage; Ruff lint and 24-file format check; mypy for 10 production modules and separately the release smoke (11 files together); tox lint and py313 environments, with py313 repeating 213 tests at 100%; `npm ci` (97 packages audited), `npm audit` (0 vulnerabilities), Vue typecheck, Vitest 12/12 in 4 files, Vite production build (4 packaged artifacts), and Playwright Chromium 2/2; `git diff --check`; two successful `uv build` runs; final wheel manifest/help/template checks; and the real isolated-wheel release smoke. Full automated coverage includes stdout isolation, deterministic/multi-dot/configured/explicit outputs, transactional overwrite and failure cleanup, all required geometry rotations/CropBoxes/origins/page sizes, review preload/edit/remove/replace/save/no-download behavior, L0 rendering/transparency, L1 whole-revision integrity and tamper detection, signed-input protection across supported modes, and one-shot loopback session/API security. The only warning is the existing upstream Starlette AnyIO `BlockingPortal` deprecation warning. No release blocker, functional correction, dependency change, ADR, or follow-up task was found.

Final artifact clarification: a wording-only README correction changed distribution metadata after the first recorded checksum. The final rebuilt artifacts supersede the earlier hashes: wheel SHA-256 `87712536713280ba182679b1c0d3ff1018449baf3812973556ac7ffffc3161e9`; sdist SHA-256 `7625450908c4be5e00097fc94a140080faa4905d6c8ce262fc26490666b6e137`. The final wheel was installed into another fresh Python 3.13.15 venv and the complete Node-free auto/review/L1/security/signature-guard smoke passed again.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @human
created: 2026-09-04 20:54
---
The human requested implementation and release verification of TASK-001.13 only, with all functional subtasks left In Progress pending human acceptance.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed release documentation and cross-cutting verification without changing product behavior. `README.md` now documents the actual Python 3.13 `pdf-signoff` Click command and Onacol YAML model, review/auto/profile/output/overwrite/signed-input workflows, L0/L1 semantics and PKCS#12 handling, loopback security assumptions, rejected inputs, the complete MVP non-goal list, and the external agent/workflow responsibility boundary. Expanded `tests/e2e/wheel_smoke.py` to exercise installed auto and review saves, safe overwrite, live session security, L1 integrity with generated self-signed credentials, and signed-input protection.

Important packaging choice: final Hatch wheel inspection proved recursive package inclusion already ships bundled YAML and all production frontend assets, so no redundant force-include configuration was added. The final wheel was installed into a fresh Python 3.13.15 environment and all smokes ran with Node absent from PATH.

Verification passed: 213 Python tests and 739/739 statements at 100.00% coverage; Ruff lint/24-file format; mypy; tox lint and py313; frozen uv sync and lock check; npm clean install/audit with 0 vulnerabilities; Vue typecheck; 12 Vitest tests in 4 files; Vite build with 4 packaged frontend artifacts; 2 Chromium Playwright workflows; git diff check; sdist/wheel builds and wheel manifest/help/config-template checks; and the expanded real isolated-wheel auto/review/L1/security/signature-guard smoke.

Known limitation: one upstream Starlette AnyIO `BlockingPortal` deprecation warning remains. No functional corrections, dependency changes, blockers, ADRs, or follow-up tasks were introduced. TASK-001.13 remains In Progress for human acceptance as requested.
<!-- SECTION:FINAL_SUMMARY:END -->
