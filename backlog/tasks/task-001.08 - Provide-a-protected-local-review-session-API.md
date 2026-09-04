---
id: TASK-001.08
title: Provide a protected local review-session API
status: To Do
assignee: []
created_date: '2026-09-04 18:03'
labels: []
dependencies:
  - TASK-001.07
references:
  - docs/pdf-sign-implementation-spec.md#11-web-serverapi
  - docs/pdf-sign-implementation-spec.md#12-local-server-security
parent_task_id: TASK-001
priority: high
type: feature
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The browser is an untrusted local frontend for one fixed signing invocation, not a general PDF service. Provide a short-lived FastAPI/Uvicorn session that exposes only the selected document, signature, safe metadata, and validated save operation while reusing the L0 backend pipeline.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A signing session binds to loopback by default, supports an ephemeral port, and lasts for exactly one CLI signing session
- [ ] #2 A random high-entropy token is established through the browser URL or secure same-session cookie and every API operation rejects requests outside the active session
- [ ] #3 The API serves only the invocation-selected PDF and PNG, session metadata, static frontend, and placement-only save request; it accepts no filesystem paths and exposes no generic file or directory access
- [ ] #4 No permissive CORS policy allows unrelated pages to issue signing requests
- [ ] #5 The save endpoint validates placements with the shared model, runs the shared stamping and output pipeline, and returns only `{ "ok": true }` after success
- [ ] #6 API tests cover authorized and unauthorized access, exact-file serving, safe session metadata, malformed save requests, and absence of path-based access
<!-- AC:END -->
