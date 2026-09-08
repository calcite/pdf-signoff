---
id: TASK-013
title: Pin the npm audit severity threshold in CI and release
status: Done
assignee:
  - '@opencode'
created_date: '2026-09-07 08:26'
updated_date: '2026-09-08 08:51'
labels:
  - code-review
dependencies: []
references:
  - .github/workflows/ci.yml
  - .github/workflows/release.yml
documentation:
  - release_guide.md
priority: low
type: chore
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Both `.github/workflows/ci.yml` and `.github/workflows/release.yml` run bare `npm audit`, which exits non-zero on an advisory of any severity anywhere in the transitive dev tree.

In the release workflow this sits before the build, publish, and GitHub Release jobs, so a newly published low-severity advisory in a build-time dependency blocks a tagged release with no change to this codebase. Recovery then requires a new version and a new tag, because the guide correctly forbids reusing a failed tag.

Choose an explicit threshold so the gate reflects a policy rather than the ambient state of npm advisories.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Both workflows pass an explicit `--audit-level` reflecting a stated policy
- [x] #2 Advisories below the threshold do not fail CI or block a release
- [x] #3 The release guide states the threshold and how to handle an advisory that does breach it
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Define a high-severity npm audit gate that permits low and moderate advisories.
2. Apply the explicit threshold to frontend audit commands in CI and release.
3. Document the release policy and recovery procedure, then validate the changed files.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Investigation confirmed bare npm audit commands in both referenced workflows. Implemented a high threshold: low and moderate findings remain reported but do not fail CI or releases; high and critical findings remain blocking. Updated release_guide.md with the local command and tagged-release breach recovery. Verification: frontend npm audit --audit-level=high reported 0 vulnerabilities; git diff --check passed.

Final verification: npm audit --help lists high as a supported --audit-level value; npm audit --audit-level=high completed successfully with 0 vulnerabilities; git diff --check passed. No YAML workflow linter is installed in this environment, so GitHub Actions remains the platform-level syntax validation.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Pinned CI and release frontend audits to --audit-level=high. The release guide now states that low and moderate advisories are non-blocking, while high and critical advisories block delivery, and documents the required new-version/new-tag recovery for a tagged breach. Verified npm audit --help supports the selected level, the audit completes with 0 vulnerabilities, and git diff --check passes. No YAML workflow linter is available locally; GitHub Actions will validate workflow syntax on review.
<!-- SECTION:FINAL_SUMMARY:END -->
