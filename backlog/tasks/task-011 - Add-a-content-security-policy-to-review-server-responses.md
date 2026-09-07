---
id: TASK-011
title: Add a content security policy to review server responses
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:26'
updated_date: '2026-09-07 16:51'
labels:
  - code-review
dependencies: []
references:
  - pdf_signoff/server.py
documentation:
  - docs/pdf-sign-implementation-spec.md
modified_files:
  - pdf_signoff/server.py
  - tests/test_server.py
priority: low
type: enhancement
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`_harden` sets only `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. There is no `Content-Security-Policy` and no framing restriction, and the middleware does not check the `Host` header against the address it bound to.

The 256-bit session token is what actually stops unrelated pages and DNS-rebinding attempts, and it does that job, so this is hardening rather than a live hole. But the review page renders an arbitrary user-supplied PDF through PDF.js, all assets are first-party and bundled, and the app loads nothing from the network. A strict policy costs nothing and matches the posture the README already claims for review mode.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Responses carry a policy that permits only same-origin assets and forbids framing
- [x] #2 A Host header allowlist limits requests to the address the server bound to
- [x] #3 PDF.js rendering, the worker module, and the signature image still load under the policy, confirmed by the Playwright end-to-end run
- [x] #4 A server test asserts the headers on both an API response and an error response
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a response CSP that permits required same-origin frontend resources, blocks embedding, and preserves inline placement styles.
2. Add an app-level Host allowlist checked by session middleware; configure it to the precise loopback host and bound port before Uvicorn serves requests.
3. Extend server tests for CSP/framing headers on successful and error API responses and for rejected Host headers.
4. Run focused Python tests and the Playwright review flow to verify PDF.js, its worker, and the signature image load under the policy.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation: ReviewServer binds the ephemeral port in start(), so the app-level allowlist must be updated there before starting Uvicorn. The frontend uses a same-origin PDF.js worker module and Vue inline placement styles.

Implemented a strict app-level Host allowlist that ReviewServer replaces with its exact loopback host and selected port before Uvicorn starts. Added a CSP covering same-origin scripts, worker, images, fetches, fonts, and required inline placement styles, with object loading, base URLs, and framing blocked. Focused checks passed: uv run pytest tests/test_server.py (40 passed), uv run ruff check pdf_signoff/server.py tests/test_server.py, uv run mypy pdf_signoff/server.py, and npm run test:e2e (2 passed).

Full regression validation passed: uv run pytest (230 passed, one third-party TestClient deprecation warning), npm run test (20 passed), and npm run typecheck. git diff --check passed.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-09-07 16:51
---
Ready for human review. All acceptance criteria have automated verification evidence.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a same-origin CSP that blocks framing, object loading, and base URLs while allowing the bundled PDF.js worker, signature image, and required inline placement styles. ReviewServer now replaces the test-only Host allowlist with its exact bound loopback host and port before serving requests. Added server coverage for CSP headers on API/error responses and for live forged-Host rejection. Verified with focused server tests, Ruff, mypy, full Python/frontend suites, and Playwright review E2E; no known limitations or follow-up tasks. No ADRs created.
<!-- SECTION:FINAL_SUMMARY:END -->
