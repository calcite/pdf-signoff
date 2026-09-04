---
id: TASK-001.11
title: Add L1 cryptographic integrity signing
status: To Do
assignee: []
created_date: '2026-09-04 18:04'
labels: []
dependencies:
  - TASK-001.07
references:
  - docs/pdf-sign-implementation-spec.md#15-l1-implementation
  - docs/pdf-sign-implementation-spec.md#22-3-l1-integration-tests
parent_task_id: TASK-001
priority: medium
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Some approvals need tamper evidence in addition to the visible PNG. Add an optional second stage that signs the completed L0 revision with a configured PKCS#12 credential while keeping identity assurance, timestamping, and long-term validation explicitly outside the product claim.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `--level l1` first creates the same approved visual result as L0 and then applies an invisible pyHanko PDF signature over that complete revision
- [ ] #2 A configured `.p12` or `.pfx` signer and reason are loaded after path expansion, with the password read from the configured environment variable and any TTY fallback using a secure prompt
- [ ] #3 Passwords, private-key material, and sensitive signer data never appear in command arguments, stdout, stderr, or logs
- [ ] #4 Missing or invalid signer credentials fail clearly without committing output or emitting profile JSON
- [ ] #5 Tests using generated self-signed credentials verify cryptographic integrity despite untrusted certificate status, preservation of the visual PNG, and failed integrity after tampering
- [ ] #6 The implementation does not add a visible cryptographic field appearance, TSA timestamping, revocation embedding, trust management, or claims of verified human identity
<!-- AC:END -->
