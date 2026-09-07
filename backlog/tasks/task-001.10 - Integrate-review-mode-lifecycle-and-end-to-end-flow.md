---
id: TASK-001.10
title: Integrate review-mode lifecycle and end-to-end flow
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:04'
updated_date: '2026-09-07 07:11'
labels: []
dependencies:
  - TASK-001.09
references:
  - docs/pdf-sign-implementation-spec.md#10-7-save
  - docs/pdf-sign-implementation-spec.md#20-2-review-mode
  - docs/pdf-sign-implementation-spec.md#22-6-frontend-tests
modified_files:
  - .gitignore
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/tsconfig.json
  - frontend/vite.config.ts
  - frontend/playwright.config.ts
  - frontend/e2e/browser-capture.mjs
  - frontend/e2e/review.spec.ts
  - pdf_signoff/cli.py
  - pdf_signoff/server.py
  - pdf_signoff/web_dist/index.html
  - pdf_signoff/web_dist/assets/index-BE55AXhf.css
  - pdf_signoff/web_dist/assets/index-gWASEKrn.js
  - pdf_signoff/web_dist/assets/pdf.worker.min-wgc6bjNh.mjs
  - tests/test_cli.py
  - tests/test_package_foundation.py
  - tests/test_review_lifecycle.py
  - tests/e2e/create_review_fixture.py
  - tests/e2e/browser_capture.py
  - tests/e2e/wheel_smoke.py
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The default CLI workflow must coordinate browser launch, one-shot server lifetime, backend save completion, final profile emission, and interruption cleanup. Integrate the completed API and frontend into an installed command and prove that human edits, rather than suggested coordinates, become the final signed state.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Review mode starts the protected local server, opens the tokenized browser URL when configured, and preloads coordinates only after profile/document validation succeeds
- [x] #2 A successful browser save completes output before responding, emits exactly one profile containing the edited final placements on CLI stdout, logs status only to stderr, shuts down after the response, and exits zero
- [x] #3 Closing the browser without saving leaves the CLI waiting, while Ctrl+C cleanly stops the server, removes temporary files, emits no profile JSON, and uses the normal interrupted-process status
- [x] #4 The Vite production build is packaged into the Python distribution so an installed review workflow requires no Node runtime
- [x] #5 A Playwright test preloads, drags, resizes, removes, replaces, and saves a signature, then asserts the output and emitted edited profile
- [x] #6 End-to-end coverage also verifies a no-coordinates session starts empty and no save dialog or browser download occurs
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a review-mode CLI runner that loads and validates any optional profile before server/browser startup, serves the packaged frontend through the protected ReviewSession/ReviewServer, honors host/port/default width/open-browser configuration, waits indefinitely for the response-complete result, and emits only the final edited profile on stdout after clean one-shot shutdown.
2. Preserve Click-native interruption semantics while guaranteeing context-managed Uvicorn/session cleanup, no profile emission, stderr-only status, and continued waiting when an opened browser exits without saving; add focused CLI lifecycle tests for startup ordering, browser configuration, save/output/profile ordering, close/wait, failure, and Ctrl+C.
3. Configure Vite to build directly into pdf_signoff/web_dist, verify Hatch's package recursion includes that static tree in built wheels, and prove an installed workflow has no Node runtime dependency.
4. Add Playwright configuration and real-process E2E fixtures that capture the configured browser URL without logging its token, exercise preload/drag/resize/remove/replace/save, validate stamped output and exact emitted edited profile, and verify empty startup plus absence of downloads/save dialogs.
5. Run frontend unit tests, typecheck and production build; real Chromium Playwright; full Python tests with 100% coverage; Ruff, mypy, package build/inspection, and isolated-wheel review/auto smoke tests. Synchronize task criteria/evidence/final summary while leaving it In Progress for human acceptance.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation confirms ReviewSession.save completes validation, stamping, and atomic output before /api/save responds; its Starlette background task sets the result event only after the response body is sent, providing the required shutdown boundary. ReviewServer already pre-binds loopback ports, suppresses token-bearing access logs, and closes the session contextually. CLI currently runs only automatic L0 and review mode returns immediately. Frontend already implements unified preload/add/move/resize/remove/save state and no browser download path. Vite currently writes frontend/dist, and pyproject has no web asset inclusion. Node 20.19.2/npm 9.2.0 are present; no project Playwright dependency/browser is yet configured. The Python build module is not in the environment, so package verification should use uv build or an ephemeral uvx build rather than modifying runtime dependencies.

Implementation checkpoint: pdf_signoff.cli now runs default/explicit review L0 through the packaged frontend, validates optional profile input before browser startup, honors configured host/port/default width/open_browser, and waits on ReviewSession's post-response result before context-managed Uvicorn shutdown and one-profile stdout emission. Browser launch failure is reported only on stderr and leaves the protected session waiting; Ctrl+C emits no profile and retains Click's normal Aborted status while the server context closes. Vite now builds into pdf_signoff/web_dist, which Hatch includes automatically as package data (an explicit force-include was tested and removed because Hatch correctly detected it as a duplicate).

Playwright 1.62.1 E2E launches the actual CLI, captures the configured tokenized browser URL through a short-lived browser helper, and passed real Chromium tests for preload, drag, asserted resize, context removal, replacement, save, stamped PDF image, exact edited emitted placements, no download/file chooser, empty startup, browser-close waiting, and SIGINT cleanup. Chromium initially lacked libglib in the sandbox; `npx playwright install chromium` plus the non-destructive documented `npx playwright install-deps chromium` resolved this. The project now has 190 Python tests at 100% coverage. A built wheel contains index/CSS/JS/PDF.js worker assets, and an isolated wheel environment passed both auto and review smokes with PATH restricted so Node was unavailable.

Final verification evidence (2026-09-04): `npm test` passed 12/12 Vitest tests; `npm run typecheck`, `npm run build`, and `npm audit` passed, with Vite producing index.html, CSS, application JS, and the PDF.js worker under pdf_signoff/web_dist. `npm run test:e2e` passed 2/2 real Chromium Playwright scenarios against the actual CLI process. `uv run pytest --cov=pdf_signoff --cov-report=term-missing tests/` passed 190/190 at 100.00% coverage. `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy pdf_signoff`, `uv lock --check`, and `git diff --check` passed. `uv build` produced both sdist and wheel; wheel inspection confirmed all four frontend artifacts. A fresh venv installed only the built wheel plus runtime dependencies, then passed automatic and protected review saves with Node absent from PATH, exact profile output, and stamped PDFs.

Known caveat: Python tests retain one upstream Starlette deprecation warning for its AnyIO BlockingPortal alias. Playwright browser/dependency installation was required in this minimal sandbox but is development/test tooling only; installed application runtime does not require Node or Playwright. No blockers, follow-up tasks, or ADRs were introduced.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Human
created: 2026-09-07 07:11
---
The human reviewed the implementation and confirmed it works; accepted for completion.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the default/explicit L0 review lifecycle around the protected one-shot Uvicorn session: optional profiles are validated before launch, configured browser opening receives only the tokenized URL, output completes before response, shutdown waits for response completion, and the CLI emits exactly one edited final profile on stdout with status on stderr. Browser-close waiting and Ctrl+C cleanup retain normal Click interruption behavior with no output/profile artifacts.

Vite now builds committed production assets directly into the Python package; Hatch includes them in the wheel without custom duplication, and an isolated installed-wheel smoke proved review and auto operation with Node absent from PATH. Added real-process Playwright tests for preload, drag, resize, remove, replace, save, stamped output, emitted edited coordinates, empty startup, no download/file chooser, browser close, and SIGINT.

Verification passed: 12 Vitest tests, frontend typecheck/build/audit, 2 Chromium Playwright E2E tests, 190 Python tests at 100% coverage, Ruff lint/format, mypy, lock/diff checks, sdist/wheel build and content inspection, and fresh-venv wheel review/auto smokes. Known limitation is one upstream Starlette deprecation warning; no blockers, follow-ups, or ADRs. Left In Progress for human acceptance as requested.
<!-- SECTION:FINAL_SUMMARY:END -->
