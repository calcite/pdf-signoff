---
id: TASK-017
title: Update frontend dependencies to unblock the release audit gate
status: In Review
assignee:
  - '@opencode'
created_date: '2026-10-25 20:00'
updated_date: '2026-10-25 20:06'
labels: []
dependencies: []
references:
  - frontend/package.json
  - frontend/package-lock.json
  - .github/workflows/release.yml
  - .github/workflows/ci.yml
priority: high
type: bug
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The 0.2.0 release build stops at npm audit --audit-level=high with six findings: vulnerable happy-dom, source-map-js, Vite, and the Vitest 3 mocker/tinypool tree. The existing high-severity audit policy is intentional (TASK-013). Update affected dependencies to patched compatible releases and verify the frontend and packaged assets under the CI toolchain.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A clean npm ci followed by npm audit --audit-level=high passes with patched locked dependency versions and no audit-policy bypass.
- [x] #2 Frontend typechecking, the full Vitest suite, production build and Playwright review flows pass after any necessary compatibility fixes.
- [x] #3 Committed packaged frontend assets match a fresh production build and retain the working PDF review flow.
- [x] #4 Release notes and durable task notes identify the dependency changes, verification and any remaining release limitations.
- [x] #5 Release recovery metadata and changelog identify patch version 0.2.1, with existing v0.2.0 left intact.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Pin patched Vitest 4.1.12 (removes the vulnerable tinypool dependency and updates mocker), happy-dom 21.0.4 and Vite 7.3.7; refresh source-map-js to 1.2.2 in the lockfile. Keep exact direct-version pins.
2. Install cleanly and run the existing high-severity audit gate. Adapt tests only if the necessary Vitest/happy-dom upgrades require it.
3. Run typecheck, all frontend unit tests, production build and real Playwright review E2E using CI Node 22 where available. Check build reproducibility against the newly generated committed assets.
4. Document the fix in the release notes and task, record verification, and move to human review.

5. Prepare patch version 0.2.1 in Python metadata/lockfile and changelog, following the documented failed-tag release recovery procedure.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial audit reproduced all six user-reported findings. Existing direct pins: vite 7.3.6, vitest 3.2.7, happy-dom 20.14.0. Registry has patched Vitest 4.1.12 with no tinypool dependency; all chosen updates support Node 20+, and CI uses Node 22. Downloaded temporary Node 22.23.4/npm 10 via npm exec to match CI without changing system Node.

Dependency update checkpoint: pins are now Vite 7.3.7, Vitest 4.1.12 and happy-dom 21.0.4; source-map-js resolves to 1.2.2. npm 10.9.9 crashed while generating the changed lockfile (Arborist optional-peer loadPeerSet edgesOut null); npm 11.21.1 generated it successfully. A subsequent clean npm ci and npm audit --audit-level=high under Node 22.23.4/npm 10.9.9 both passed with zero vulnerabilities, so no special npm version or flags are needed by CI consumers. npm ls confirms the patched versions and no tinypool. Typecheck, 23 Vitest tests and the Vite production build passed without source or test changes. The build produces the same packaged assets as HEAD.

Final verification on Node 22.23.4/npm 10.9.9: clean npm ci passed; npm audit --audit-level=high reported zero vulnerabilities; npm run typecheck passed; npm test passed all 23 tests in four files; npm run build passed with Vite 7.3.7; git -C .. diff --exit-code -- pdf_signoff/web_dist passed, demonstrating the generated assets exactly match HEAD; npm run test:e2e passed both real Chromium review flows. No source/test compatibility changes were needed. Browser binaries and host libraries were already installed in the sandbox.

Release recovery metadata: pyproject.toml, pdf_signoff.__version__ and editable uv.lock package entry now report 0.2.1; CHANGELOG.md has a dated patch-release entry naming all dependency fixes. uv lock --check passed, uv run pdf-signoff --version printed 0.2.1, uv run pytest tests/test_cli.py tests/test_package_foundation.py passed 43 tests, and git diff --check passed. Existing v0.2.0 tag remains in place; retry publication from a new v0.2.1 tag after the fix is committed. Remote GitHub Actions/PyPI publication was not run in this session. No follow-up tasks or ADRs were needed; these are patched versions of existing build/test dependencies.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @opencode
created: 2026-10-25 20:01
---
**Human:** Reported the release frontend step failing at npm audit --audit-level=high, with six findings including critical tinypool and high happy-dom/Vite/source-map-js vulnerabilities.
---

author: @opencode
created: 2026-10-25 20:01
---
**Agent:** Registry metadata confirms patched Vitest 4.1.12, happy-dom 21.0.4 and Vite 7.3.7 support the current Node toolchain. A local v0.2.0 tag exists; following release_guide.md recovery, include 0.2.1 metadata/changelog preparation for the fix rather than reuse the failed tag.
---

author: @opencode
created: 2026-10-25 20:06
---
**Agent:** Ready for human review. The reported frontend CI gate passes locally under Node 22 with zero audit findings, 23 unit tests and two browser E2E tests. Release recovery is prepared as 0.2.1 according to the guide; use a new v0.2.1 tag after committing this fix.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Updated exact frontend pins to Vite 7.3.7, Vitest 4.1.12 and happy-dom 21.0.4, and locked source-map-js to 1.2.2. The Vitest upgrade removes vulnerable tinypool and supplies patched mocker. Clean npm ci and the existing high audit gate now report zero vulnerabilities on Node 22/npm 10; typecheck, 23 unit tests, production build and two Playwright workflows pass. Bundled assets are byte-identical to HEAD. Prepared 0.2.1 metadata and dated release notes for failed-tag recovery; lockfile/version checks, 43 Python CLI/package tests and diff checks pass. npm 11 was needed only to generate the updated lockfile after an npm 10 optional-peer resolver crash; npm 10 consumes it successfully. GitHub/PyPI publication remains pending a new v0.2.1 tag after commit. No follow-up tasks or ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
