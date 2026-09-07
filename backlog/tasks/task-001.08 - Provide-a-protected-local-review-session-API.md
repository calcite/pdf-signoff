---
id: TASK-001.08
title: Provide a protected local review-session API
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-04 18:03'
updated_date: '2026-09-07 07:11'
labels: []
dependencies:
  - TASK-001.07
references:
  - docs/pdf-sign-implementation-spec.md#11-web-serverapi
  - docs/pdf-sign-implementation-spec.md#12-local-server-security
modified_files:
  - pdf_signoff/server.py
  - tests/test_server.py
  - pyproject.toml
  - uv.lock
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The browser is an untrusted local frontend for one fixed signing invocation, not a general PDF service. Provide a short-lived FastAPI/Uvicorn session that exposes only the selected document, signature, safe metadata, static frontend assets, and validated save operation while reusing the L0 backend pipeline. This subtask provides the protected one-shot backend and lifecycle seams; Vue implementation and CLI/browser orchestration and automatic shutdown are TASK-001.09 and TASK-001.10.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A review server binds only to a loopback IP by default, supports an OS-selected ephemeral port, owns exactly one one-shot review session, and exposes explicit result/stop seams for later CLI lifecycle integration
- [x] #2 A random token with 256 bits of entropy is established through the browser URL into an HttpOnly SameSite=Strict session cookie (or accepted as a bearer credential), and every route rejects requests outside the active session
- [x] #3 The API serves only the invocation-selected PDF and PNG, path-free session metadata, constrained static frontend assets, and a placement-only save request; it accepts no filesystem paths and exposes no generic file or directory access
- [x] #4 No permissive CORS policy is installed, and explicit Origin/Sec-Fetch-Site checks reject unrelated browser origins
- [x] #5 The save endpoint validates placements with the shared model, runs the shared stamping and atomic output pipeline, builds the final profile, consumes the session after the response, and returns only `{ "ok": true }` after success
- [x] #6 API/server tests cover authorized and unauthorized access, token bootstrap and expiry, exact-file and constrained-static serving, safe metadata, malformed/path-bearing save requests, shared output, loopback/ephemeral binding, logging secrecy, and absence of path-based access
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Replace the server placeholder with an isolated `ReviewSession` that captures only fixed invocation paths and inspected metadata, generates a 256-bit token, tracks active/saving/saved state safely, validates placement-only requests through `validate_placements`, and commits through `stamp_l0` plus `build_final_profile`.
2. Build a FastAPI application whose URL-token bootstrap establishes an HttpOnly SameSite=Strict cookie, whose bearer/cookie middleware protects every route and rejects cross-origin requests, and whose only resources are safe session metadata, the fixed PDF/PNG, exact static frontend assets, and save; disable schema/docs and avoid CORS middleware.
3. Add a loopback-only Uvicorn handle that pre-binds a socket so port 0 exposes its selected ephemeral port, runs with access logging disabled and all server logging directed to stderr, and supports explicit stop/context-manager cleanup for later CLI lifecycle integration.
4. Add comprehensive API and real-server tests for token entropy/bootstrap/authentication/inactivation, fixed-file and metadata boundaries, static traversal rejection, malformed/path-bearing/cross-origin save requests, shared stamping/output behavior and retry semantics, loopback/ephemeral binding, actual HTTP smoke, and stdout/logging secrecy.
5. Run focused and full pytest at 100% coverage, Ruff format/lint, mypy, tox where practical, lock/diff checks, and API/Uvicorn smoke checks; then synchronize task evidence without moving it from In Progress.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial investigation found `pdf_signoff/server.py` as a one-line placeholder and review-mode CLI as an invocation handoff only. Existing shared seams are conservative PDF/PNG inspection, profile matching, strict `Placement`/`validate_placements`, `stamp_l0` with aspect checking and atomic publication, and `build_final_profile`; these are reused rather than duplicated.

Implementation result: `ReviewSession` captures fixed private invocation paths and inspected objects, creates a `secrets.token_urlsafe(32)` credential (256 random bits), serializes only page count/initial placements/default width, coordinates concurrent active/saving/saved/closed state, allows retry after pipeline failure, and publishes a final profile only after a successful response background step. `prepare_review_session` performs input inspection and optional profile matching.

`create_review_app` disables OpenAPI/docs, has no CORS middleware, sanitizes request-validation and pipeline failures, applies no-store/nosniff headers, verifies Origin or Sec-Fetch-Site, and protects every route. A valid token is accepted only for the root bootstrap and redirected into an HttpOnly SameSite=Strict session cookie; bearer auth is also available. The fixed PDF and PNG have dedicated endpoints. Static serving is restricted to one validated `index.html` and its `assets/` directory through Starlette traversal-safe static handling; there is no listing or generic path route. The cookie intentionally omits the `Secure` attribute because this loopback server uses HTTP, not TLS.

`ReviewServer` rejects non-loopback IPs, pre-binds its socket so configured port 0 yields an observable ephemeral port, supports explicit ports and context-managed shutdown, directs Uvicorn logs to stderr, disables access logging so token-bearing bootstrap URLs are not normally logged, and closes its session on stop. Successful save rejects all later requests immediately; TASK-001.10 will consume `wait_for_result`, emit the final profile on CLI stdout, and stop the process after the response. TASK-001.09 will supply packaged Vue assets. No ADR was needed because these choices implement the task-local security contract.

Verification: focused `tests/test_server.py` passed 37/37 at 100% `server.py` coverage. Full `uv run pytest --cov=pdf_signoff --cov-report=term-missing tests/` passed 183/183 at 100% project coverage. Tests include a real Uvicorn/HTTP smoke on 127.0.0.1 with port 0, fixed-resource byte equality, actual atomic PDF stamping/reopen, source-hash preservation, token/cookie/auth/inactivation, static traversal and generic-path rejection, sanitized malformed/path-bearing requests, cross-origin denial/no CORS headers, stdout emptiness and token absence from captured logs, explicit-port operation, and startup/cleanup failures. `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy pdf_signoff`, `uv lock --check`, `git diff --check`, both `uv run tox` environments, and `uv build` passed. One upstream Starlette warning remains for its deprecated AnyIO alias; there are no project warnings, blockers, follow-up tasks beyond already-scoped TASK-001.09/TASK-001.10, or ADRs.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @human
created: 2026-09-04 19:55
---
**Human:** Implement only TASK-001.08 from a fresh context; prerequisites through L0 are implemented and verified but await acceptance. Deliver the protected one-session FastAPI/Uvicorn API, comprehensive security/API/server verification, clean later-task interfaces, and leave the task In Progress.
---

author: Human
created: 2026-09-07 07:11
---
The human reviewed the implementation and confirmed it works; accepted for completion.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the protected one-shot review backend without adding Vue UI or CLI orchestration. The new FastAPI session exposes only fixed selected resources, safe metadata, constrained frontend assets, and strict placement-only saving through the existing inspection/validation/stamping/atomic-output/profile pipeline. It uses a 256-bit token, URL-to-HttpOnly/SameSite cookie bootstrap plus bearer support, constant-time comparison, cross-origin rejection, sanitized errors, session consumption after save, loopback-only Uvicorn binding, port-0 discovery, explicit lifecycle/result seams, stderr-only server logging, and disabled access logs.

Added 37 comprehensive API/server tests and the current Starlette `httpx2` test dependency. Full verification passed: 183 tests and 100% project coverage, focused 100% server coverage, real Uvicorn/HTTP and PDF-output smoke, Ruff format/lint, mypy, lock/diff checks, tox lint/Python 3.13 environments, and package build. Known limitation: loopback HTTP means the session cookie is HttpOnly and SameSite=Strict but not `Secure`; the high-entropy credential, origin checks, loopback restriction, no CORS, and one-shot invalidation remain the security boundary. Existing TASK-001.09 supplies Vue assets and TASK-001.10 wires browser/CLI startup, post-response server shutdown, and stdout emission. No blockers, new follow-up tasks, or ADRs. Left In Progress for human acceptance as requested.
<!-- SECTION:FINAL_SUMMARY:END -->
