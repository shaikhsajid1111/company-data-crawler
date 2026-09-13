# Publishing to PyPI

This project publishes to PyPI **automatically** whenever a GitHub Release is
published. The pipeline uses **PyPI Trusted Publishing (OIDC)**, so there are
no API tokens or secrets to manage. Manual publishing from your machine is
also documented below as a fallback.

## How the pipeline works

Publishing a GitHub Release triggers
[`.github/workflows/publish.yml`](.github/workflows/publish.yml), which runs
three jobs in order:

1. **tests** — installs the project with `uv sync` and runs the offline test
   suite (`test.py`). A red test suite never reaches PyPI.
2. **build** — verifies that the release tag, `pyproject.toml` and the
   package `__version__` all agree, then builds the sdist and wheel with
   `uv build` and uploads them as a workflow artifact.
3. **publish** — downloads the artifacts and uploads them to PyPI with
   [`pypa/gh-action-pypi-publish`](https://github.com/pypa/gh-action-pypi-publish)
   using OIDC Trusted Publishing (`environment: pypi`, `id-token: write`).

## One-time setup: PyPI Trusted Publishing (recommended)

1. Create a [PyPI](https://pypi.org) account (with verified email) if you do
   not have one.
2. Go to **<https://pypi.org/manage/account/publishing/>** and add a new
   **pending publisher** with these exact values:

   | Field | Value |
   | ----- | ----- |
   | PyPI project name | `company-data-crawler` |
   | Owner | `shaikhsajid1111` |
   | Repository | `company-data-crawler` |
   | Workflow filename | `publish.yml` |
   | Environment name | `pypi` |

   Per the PyPI docs, a *pending* publisher does **not** reserve the project
   name — the project is created on the **first successful publish**. If
   someone else registers the name first, the pending publisher is
   invalidated, so cut the first release soon after setting it up.
3. On GitHub: **Settings → Environments → New environment**, name it exactly
   `pypi`. Optionally protect it (e.g. restrict to tags) for extra safety.

That is all — no secrets are stored in the repository.

## Cutting a release (the routine)

1. **Bump the version** in two places — they must match:
   - `project.version` in `pyproject.toml`
   - `__version__` in `src/company_data_crawler/__init__.py`

   The CI version gate requires them to equal the release tag (a leading `v`
   on the tag is fine: tag `v0.2.0` ↔ version `0.2.0`).
2. Update docs/README/changelog as needed, commit and push to `main`:

   ```bash
   git add -A && git commit -m "Bump version to 0.2.0" && git push
   ```

3. **Tag and push the tag:**

   ```bash
   git tag -a v0.2.0 -m "Release 0.2.0"
   git push origin v0.2.0
   ```

4. **Create the GitHub Release:** *Releases → Draft a new release* → choose
   the `v0.2.0` tag → add release notes → **Publish release**.
5. Watch the run under the **Actions** tab. When the `publish` job finishes,
   the new version is live on
   <https://pypi.org/project/company-data-crawler/>.
6. Verify in a clean environment (the PyPI index can lag a minute or two):

   ```bash
   uv run --with company-data-crawler==0.2.0 \
       python -c "import company_data_crawler as c; print(c.__version__)"
   ```

## Alternative: publishing with an API token

If you prefer a token over OIDC:

1. Create a token at **<https://pypi.org/manage/account/token/>** (scope it to
   the project once it exists).
2. Add it as the GitHub repository secret `PYPI_API_TOKEN` (**Settings →
   Secrets and variables → Actions**).
3. In `.github/workflows/publish.yml`, change the `Publish to PyPI` step to:

   ```yaml
   - name: Publish to PyPI
     uses: pypa/gh-action-pypi-publish@release/v1
     with:
       password: ${{ secrets.PYPI_API_TOKEN }}
   ```

   and remove the `environment: pypi` key and the `id-token: write`
   permission (they are only needed for Trusted Publishing).

## Optional: TestPyPI dry run

Rehearse a release against [TestPyPI](https://test.pypi.org) first:

1. On <https://test.pypi.org/manage/account/publishing/>, add the same
   pending publisher (project name, owner, repo, workflow `publish.yml`,
   environment `testpypi`) and create a matching `testpypi` GitHub
   environment — or just use a TestPyPI token locally.
2. Publish manually from your machine:

   ```bash
   uv build
   UV_PUBLISH_TOKEN=pypi-xxxxxxxx uv publish \
       --publish-url https://test.pypi.org/legacy/
   ```

3. Install from TestPyPI to check the artifact:

   ```bash
   uv pip install \
       --index-url https://test.pypi.org/simple/ \
       --index-strategy unsafe-best-match \
       company-data-crawler
   ```

## Publishing manually from your machine

No GitHub required — `uv` can build and upload directly:

```bash
# from a clean checkout of the exact commit you want to ship
uv build          # -> dist/*.tar.gz and dist/*.whl
uv publish        # prompts for credentials, or:
UV_PUBLISH_TOKEN=pypi-xxxxxxxx uv publish
```

Notes:

- The project name must be available:
  <https://pypi.org/project/company-data-crawler>
- PyPI never allows re-uploading the same version — bump the version and
  rebuild instead of retrying a failed-name upload.
- Inspect the artifacts before publishing: `tar -tf dist/*.tar.gz` and
  `unzip -l dist/*.whl`.

## Troubleshooting

| Problem | Cause & fix |
| ------- | ----------- |
| `400 File already exists` | That version is already on PyPI. PyPI never allows re-uploads — bump the version, re-tag and release again. |
| `Trusted publishing could not be validated` | The pending publisher on PyPI must match **exactly**: owner, repository, workflow filename (`publish.yml`) and environment (`pypi`). Also confirm the publish job keeps `permissions: id-token: write` and runs from the configured repository. |
| CI fails with a version-mismatch error | The release tag, `pyproject.toml` and `__version__` must all be the same version (tag may start with `v`). Fix and cut a new release. |
| Freshly published version will not install | PyPI CDN lag. Wait a minute or two, then retry with a fresh virtualenv / `--no-cache`. |
| Project name already taken on PyPI | Choose a different `project.name` in `pyproject.toml` (and update the trusted publisher + docs), then release. |
