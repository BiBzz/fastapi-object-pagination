# Contributing

## Setting up

The project is managed with [uv](https://docs.astral.sh/uv/). One command gives
you the pinned environment, with every dependency the checks and the tests need:

```bash
uv sync
```

It uses the interpreter in `.python-version`, which is the oldest version the
library supports.

## The checks

These are the gates CI runs, in this order:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
```

CI replays them on Python 3.10, 3.11, 3.12 and 3.13, so a failure that only
shows up on a newer interpreter comes back from the pull request rather than
from your machine.

## Commits

Work branches off `development`, the default branch. Everything in the
repository is written in English, comments and test names included, and commit
messages follow [Conventional Commits](https://www.conventionalcommits.org):
`feat: ...`, `fix: ...`, `docs: ...`.

## Releasing

One command, run from `development` by a maintainer:

```bash
scripts/release.sh 0.1.2
```

It bumps the version in `pyproject.toml`, refreshes `uv.lock`, replays the four
checks above, commits as `chore(release): 0.1.2`, creates a signed `v0.1.2` tag
and, after asking, pushes the branch and the tag to both remotes, `github` and
`origin`. A second argument becomes the tag message, and `--yes` skips the
question.

It refuses to run from another branch, on a tree that differs from either
remote, on a version already declared or older than the declared one, and on a
tag that exists anywhere already. When a check fails, `pyproject.toml` and
`uv.lock` are put back as they were and nothing is committed or pushed.

### What the tag triggers

Pushing a `v*` tag to GitHub starts the `Release` workflow, which verifies the
tag matches the declared version, runs the checks again on a clean machine,
builds the wheel and the sdist, then uploads them to PyPI. The upload is
authenticated by PyPI trusted publishing over OIDC, so no API token is stored
anywhere in the repository.

The job runs in the `pypi` deployment environment, which has a required
reviewer, so the run waits until a maintainer approves it on the
[Actions tab](https://github.com/BiBzz/fastapi-object-pagination/actions).
That approval is the point of no return: a version on PyPI can be yanked, but
its files can never be replaced or uploaded again.

### Cutting a release needs

- push access to `github` and `origin`;
- a GPG key able to sign, since both the commit and the tag are signed;
- the rights to approve the `pypi` environment on GitHub.

### If a release goes wrong

Before the upload, a failed run leaves a tag behind. Delete it on both sides,
fix the problem, then run the script again with the same version:

```bash
git tag -d v0.1.2
git push github :refs/tags/v0.1.2
git push origin :refs/tags/v0.1.2
git reset --hard HEAD~1   # only while the release commit is still unpushed
```

After the upload the version is spent, because PyPI never accepts the same file
twice. Yank it there and release the next patch version instead.

### The pypi environment is not optional

A workflow that names an environment GitHub does not know gets one created on
the fly, with no protection rules, and the release then publishes with no
review at all. If this repository is forked or recreated, create the
environment before the first tag:

```bash
gh api -X PUT \
  repos/BiBzz/fastapi-object-pagination/environments/pypi --input - <<JSON
{"prevent_self_review": false, "reviewers": [{"type": "User", "id": $(gh api user --jq .id)}]}
JSON
```

`prevent_self_review` has to stay false while the reviewer is the only
maintainer, otherwise nobody is allowed to approve the run. Read the result
back with:

```bash
gh api repos/BiBzz/fastapi-object-pagination/environments --jq '.environments[].name'
```
