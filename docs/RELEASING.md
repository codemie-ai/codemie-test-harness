# Releasing

`codemie-test-harness` is released to PyPI by the GitHub Actions workflow `publish.yml`. A release starts when someone with write access publishes a GitHub Release. The harness is versioned on its own, independent of the CodeMie platform and the SDK.

| Package | Registry | Tag |
|---------|----------|-----|
| `codemie-test-harness` | PyPI | `vX.Y.Z` or `vX.Y.Z-rcN` |

A merge to `main` never releases. A tag without the `v` prefix does not publish anything: the `resolve` job fails.

## How to release

1. Merge the changes you want to release to `main`. Wait for CI to pass.
2. Choose the version. It must be higher than the highest version on PyPI and on the line in `pyproject.toml` (see below).
3. Create the Release. Use **Publish release**: **Save draft** does not start a workflow.
   - UI: Releases > Draft a new release > choose a new tag such as `v1.2.3`, target `main` > Publish release.
   - CLI: `gh release create v1.2.3 --target main --generate-notes`
4. Open the run in the Actions tab. `verify` builds and checks. `publish` waits for approval if the `release` environment has reviewers.

## How versions work

The tag is the version: `v1.2.3` releases `1.2.3`. `pyproject.toml` holds only the base line, `MAJOR.MINOR.0`.

- The tag must be `MAJOR.MINOR.PATCH` on the same `MAJOR.MINOR` line as `pyproject.toml`. The only pre-release form is `-rcN`, for example `v1.2.3-rc1`.
- The workflow stamps the version into the build only (`poetry version`). It does not commit a version change.
- To start a new line, raise the base in `pyproject.toml`, for example to `1.3.0`, and merge it. Then tag `v1.3.0`.

## Checks before anything is published

The `verify` job has no secrets. It fails, and nothing is published, when:

- the tagged commit is not on `main`;
- for a manual publish, the tag does not exist or does not point to the dispatched commit;
- the tag prefix, format or line does not match;
- the version is equal to or lower than the highest published version (`scripts/release/check_version.py`);
- lint or the build fail.

The `publish` job runs the version check again right before the upload. It runs only in `codemie-ai/codemie-test-harness`, so a fork never publishes.

`scripts/release/check_version.py` compares the version with the live PyPI registry. A timeout, network error or malformed response stops the release.

Print the version a tag names (no network):

```bash
python3 scripts/release/check_version.py --ecosystem pypi --name codemie-test-harness --tag v1.2.3 --base 1.2.0 --tag-prefix v
```

## Admin prerequisites

An administrator does these steps once. This document only lists them.

- **Repository.** Create the empty public repository `codemie-ai/codemie-test-harness` before the first sync.
- **GitHub environment `release`.** Create it in Settings > Environments. Restrict deployments to the tags `v*` (and `main` for a manual publish). Add required reviewers if a second approval is wanted.
- **Fork pull requests.** In Settings > Actions > General, require approval for workflow runs from fork pull requests.
- **PyPI trusted publisher.** Publishing uses OpenID Connect with no stored token. In the PyPI project settings add a trusted publisher with: project `codemie-test-harness`, owner `codemie-ai`, repository `codemie-test-harness`, workflow `publish.yml`, environment `release`. If the project does not exist yet, add it as a pending publisher (Account > Publishing) with the same values. Only the `publish` job has the `id-token: write` permission.
- **First commit.** Push the first exported snapshot to the new repository as a single commit. The export carries no history.
