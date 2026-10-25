# GitHub And PyPI Release Guide

This guide publishes the `pdf-signoff` package from
`git@github.com:calcite/pdf-signoff.git`. Publishing is automated by
`.github/workflows/release.yml`; do not upload the contents of `dist/` from a
workstation.

## First Push

Check the local branch name before adding the remote:

```console
git status
git branch --show-current
git remote -v
```

The commands below expect an empty GitHub repository. If it was initialized
with a README, `.gitignore`, or license, do not force-push over it. Use a local
environment that has credentials for `git@github.com:calcite/pdf-signoff.git`
to fetch and merge the remote initialization before pushing this codebase.

The current local branch is `main`. Keep `main` as the only default branch; do
not create an independent `master` history.

### Empty Remote

If GitHub has no default branch yet, add `origin` if necessary and push `main`:

```console
git remote add origin git@github.com:calcite/pdf-signoff.git
git push -u origin main
```

If `origin` already exists, use this instead of `git remote add`:

```console
git remote set-url origin git@github.com:calcite/pdf-signoff.git
```

### Remote Initialized By GitHub

If GitHub created `main` with a license, README, or `.gitignore`, retain that
initial commit and merge its unrelated history. Run these commands only from a
machine with GitHub credentials:

```console
git fetch origin main
git log --oneline HEAD..origin/main
git merge --allow-unrelated-histories origin/main
```

If Git reports a conflict, it will commonly be in `LICENSE` because both
histories contain one. Compare the attribution before resolving it:

```console
git diff HEAD origin/main -- LICENSE
```

Edit `LICENSE` to retain the intended copyright attribution and remove all
conflict markers, then finish and push the merge:

```console
git add LICENSE
git commit
git push -u origin main
```

After the first push, confirm the CI workflow succeeds on the chosen default
branch.

## Repository Setup

1. In GitHub **Settings > Actions > General**, allow workflows to create and
   approve pull requests only if the repository policy requires it. The release
   workflow itself needs the repository `GITHUB_TOKEN` to have read/write
   workflow permissions so it can create a GitHub Release.
2. In GitHub **Settings > Environments**, create an environment named `pypi`.
   Optional required reviewers provide an approval gate immediately before PyPI
   publication. The name must remain exactly `pypi` because it is part of the
   PyPI Trusted Publisher identity.
3. In PyPI, use **Your projects > Publishing > Add a new pending publisher**
   for the initial release. Set the project name to `pdf-signoff`, owner to
   `calcite`, repository to `pdf-signoff`, workflow to `release.yml`, and
   environment to `pypi`. If the project already exists, configure the same
   values under that project’s **Publishing** settings instead.
4. Do not create a PyPI API token or GitHub secret. The `publish-pypi` job uses
   GitHub Actions OIDC with `id-token: write`; PyPI verifies the repository,
   workflow filename, and environment.
5. Confirm `pdf-signoff` is available for the intended PyPI account before the
   first release. A package version cannot be replaced after publication.

## Normal Release

1. Update `project.version` in `pyproject.toml` and add the corresponding dated
   entry to `CHANGELOG.md`. Use a final PEP 440 version such as `0.1.1`; the
   workflow intentionally accepts only matching final tags such as `v0.1.1`.
2. Regenerate committed frontend assets and run the same checks as CI:

   ```console
   uv sync --locked --group dev
   uv lock --check
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy pdf_signoff
   uv run pytest --cov=pdf_signoff tests/
   cd frontend
   npm ci
    npm audit --audit-level=high
   npm run typecheck
   npm test
   npm run build
   git -C .. diff --exit-code -- pdf_signoff/web_dist
   ```

3. Commit the version, changelog, and regenerated `pdf_signoff/web_dist` files;
   push the commit to the selected default branch and wait for CI to pass.
4. Create an annotated tag from that exact commit and push it:

   ```console
   git tag -a v0.1.1 -m "Release v0.1.1"
   git push origin v0.1.1
   ```

5. The release workflow re-runs quality checks, rebuilds the frontend and
   distributions, validates that the tag equals `v` plus `project.version`,
   installs and smoke-tests the wheel, publishes to PyPI, and creates a GitHub
   Release with the wheel and source distribution attached. Approve the `pypi`
   environment if reviewers are configured.

## Frontend Audit Policy

CI and release use `npm audit --audit-level=high`. Low and moderate advisories
remain visible in the audit output but do not block CI or a release; high and
critical advisories do block them. For a high or critical breach, update or
replace the affected dependency and rerun the release checks. If a tagged
release fails before PyPI publication, follow the recovery procedure below:
correct the release commit, increment the version, and create a new matching
tag rather than bypassing the audit gate or reusing the failed tag.

## Recovery

If a workflow fails before PyPI publication, correct the release commit, create
a new version, and push a new matching tag. Do not move or reuse the failed tag.

If PyPI accepted the files but GitHub Release creation failed, run **Release**
from the Actions tab, supply the existing tag, and select **Skip PyPI**. This
uses the already-built tag to create the missing GitHub Release without trying
to overwrite the immutable PyPI version.

If PyPI publication itself reports that the version already exists, verify the
published artifacts and use the same manual **Skip PyPI** recovery only when
the existing PyPI version is the intended release. Otherwise increment the
package version, update the changelog, and release under a new tag.
