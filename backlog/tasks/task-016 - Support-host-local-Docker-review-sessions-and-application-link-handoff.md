---
id: TASK-016
title: Support host-local Docker review sessions and application link handoff
status: In Review
assignee:
  - '@opencode'
created_date: '2026-10-25 19:36'
updated_date: '2026-10-25 19:43'
labels: []
dependencies: []
references:
  - pdf_signoff/server.py
  - pdf_signoff/cli.py
priority: medium
type: enhancement
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Review sessions must be reachable through Docker port publishing to host loopback. The calling application will obtain and present the review link; the browser and entire session remain on one host. Existing loopback-only binding and bound-address Host validation prevent this deployment. The approved plan separates the listener from the browser-facing address and provides an opt-in machine-readable link handoff for CLI callers.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Any valid IPv4 or IPv6 bind address is supported, including wildcard addresses; the default remains 127.0.0.1.
- [x] #2 An optional browser-facing base URL determines the tokenized review link and exact Host allowlist independently of the listening address and port; invalid base URLs fail cleanly.
- [x] #3 CLI callers can opt into a private, atomically published version-1 session-info JSON file containing the ready review URL, with no token in stdout or routine logs. Existing destinations and output-PDF path collisions are refused; cleanup occurs on normal exit, SIGINT cancellation and handled failures.
- [x] #4 Token authentication, same-origin checks, Host validation, one-shot save and shutdown remain enforced with Docker-style addresses and ports.
- [x] #5 Help, documentation and meaningful automated checks cover host-loopback Docker publishing, link handoff and mapped-port access.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Separate ReviewServer bind IP from an optional normalized public HTTP(S) origin; use that origin for generated URLs and the exact Host allowlist. Wildcard listeners fall back to the corresponding loopback URL when no public origin is supplied.
2. Add Onacol public_url and session_info_file options. Publish a private, atomic, no-overwrite {"version":1,"url":"..."} readiness file only after server startup; remove it on normal exit, cancellation or error. Reject output-path collisions and use a shared existing directory for Docker handoff.
3. Document the deployment/interface contract in docs/adr/0001 and README; keep stdout and routine logs credential-free. Preserve existing token, same-origin and one-shot behavior.
4. Verify real wildcard HTTP serving, IPv6 where available, public-origin Host validation with a different port, CLI file-based handoff/save/cancellation/failure, and configuration layering. Run full Python tests, Ruff, mypy and diff checks.
5. Update verified criteria and final summary, leaving acceptance to the human.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation: ReviewServer accepts literal listener IPs, including wildcards, and independently normalizes an optional public_url root HTTP(S) origin. The public origin determines both the link and exact Host allowlist; absent an override, wildcard listeners use the corresponding loopback address and selected port. Existing authentication, CSP, origin checks and one-shot save are preserved.

CLI/config: public_url and session_info_file follow existing Onacol YAML/env/CLI precedence. session-info paths expand environment variables and ~. session_info.py uses private NamedTemporaryFile staging, flush and atomic no-overwrite hard-link publication of {"version":1,"url":"..."}; the context removes the readiness file on graceful exit. The path must differ from the PDF output, its parent must exist, and existing destinations including symlinks are preserved. --session-info-file is rejected in auto mode. Python integrations retain ReviewServer.url.

Verification: uv run pytest --cov=pdf_signoff --cov-report=term-missing tests/ passed 266 tests at 100% statement coverage. Coverage includes live IPv4/IPv6 wildcard HTTP serving, external-origin Host and port handling, bootstrap cookie/save/session consumption, invalid origin rejection, actual CLI subprocess file-readiness/save/SIGINT cancellation, private file mode, no-overwrite and output/symlink collisions, and configuration precedence. uv run ruff check ., uv run ruff format --check ., uv run mypy pdf_signoff and git diff --check passed. Existing upstream Starlette/AnyIO deprecation warning only.

Documentation: README contains a host-loopback Docker publish example and application handoff contract; implementation spec is updated alongside pre-existing human edits. Architectural context: docs/adr/0001-host-local-container-review-sessions.md. No existing ADR template was present, so standard Context/Decision/Consequences sections were used.

Limitations: Docker CLI is unavailable here; Docker port publishing itself was not run, while equivalent preserved Host/Origin headers were exercised over real sockets. SIGTERM/SIGKILL can leave a stale session file; callers watch process exit, use SIGINT for graceful cancellation, and clean stale files before reuse. A shared directory and matching user/file permissions are required. No follow-up tasks.

Workflow: Added In Review to backlog/config.yml because project instructions require human review and the initial configuration offered only To Do/In Progress/Done. Final acceptance remains with the human.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-10-25 19:37
---
**Human:** The entire session stays on one host. pdf-signoff runs in Docker with the port published to host loopback; another application obtains and presents the review link. Approved proceeding with the updated plan.
---

author: @opencode
created: 2026-10-25 19:37
---
**Agent:** The link-consumer interface was not specified. Implementing the proposed opt-in session-info file for CLI consumers; Python callers retain ReviewServer.url. The file is the readiness signal and keeps credentials out of logs/stdout. Existing user changes include docs/pdf-sign-implementation-spec.md and untracked HTML/release documentation.
---

author: @opencode
created: 2026-10-25 19:43
---
**Agent:** Implementation and verification are complete; ready for human review. The caller can use --host 0.0.0.0 --port 8000 --public-url http://127.0.0.1:8080 --open-browser false --session-info-file /shared/session.json, with Docker publishing 127.0.0.1:8080:8000. Read url from the shared readiness file. Docker itself was unavailable in this environment.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Enabled configurable IPv4/IPv6 listeners and a separate browser-facing public_url for host-local Docker publishing, retaining exact Host validation and session protections. Added private atomic version-1 session-info JSON handoff for applications, lifecycle cleanup and conservative collision handling. Documented deployment and interface in README, implementation spec and ADR 0001. Verified 266 Python tests at 100% coverage, Ruff lint/format, mypy and diff checks. Docker runtime validation was unavailable; live socket and CLI subprocess integration tests passed. Abrupt SIGTERM/SIGKILL may leave stale session files, as documented. No follow-up tasks; ready for human acceptance.
<!-- SECTION:FINAL_SUMMARY:END -->
