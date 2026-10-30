#!/usr/bin/env bash
#
# Cut a release: bump the version, replay the checks CI runs, then sign and
# push the tag that triggers the PyPI upload.
#
#   scripts/release.sh <version> [tag message] [--yes]
#
# It refuses to release from another branch, to release a tree that differs
# from either remote, to reuse or go backwards on a version, and to push
# anything once a check has failed.

set -euo pipefail

RELEASE_BRANCH="${RELEASE_BRANCH:-development}"
REMOTES=(github origin)

die() { printf 'release: %s\n' "$1" >&2; exit 1; }
step() { printf '\n==> %s\n' "$1"; }

assume_yes=false
args=()
for arg in "$@"; do
    case "$arg" in
        -y | --yes) assume_yes=true ;;
        -*) die "unknown option ${arg}" ;;
        *) args+=("$arg") ;;
    esac
done
[ "${#args[@]}" -ge 1 ] || die "usage: scripts/release.sh <version> [tag message] [--yes]"

version="${args[0]}"
tag="v${version}"
message="${args[1]:-}"

[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(((a|b|rc)[0-9]+)|(\.post[0-9]+))?$ ]] ||
    die "version ${version} is not of the form 1.2.3, 1.2.3rc1, 1.2.3a1, 1.2.3b1 or 1.2.3.post1"

cd "$(dirname "$0")/.."

step "Checking the working tree"
branch="$(git branch --show-current)"
[ "$branch" = "$RELEASE_BRANCH" ] ||
    die "releases are cut from ${RELEASE_BRANCH}, not ${branch}"
git diff-index --quiet HEAD -- || die "the tracked files have uncommitted changes"

declared="$(grep -c '^version = ' pyproject.toml || true)"
[ "$declared" -eq 1 ] || die "pyproject.toml declares ${declared} top-level versions, expected 1"
current="$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml)"
[ -n "$current" ] || die "cannot read the current version from pyproject.toml"
[ "$version" != "$current" ] || die "${version} is already the declared version"
# sort -V ranks 1.0.0rc1 above 1.0.0, so only plain versions are compared
if [[ "$version" =~ ^[0-9.]+$ && "$current" =~ ^[0-9.]+$ ]]; then
    [ "$(printf '%s\n%s\n' "$current" "$version" | sort -V | tail -1)" = "$version" ] ||
        die "${version} is older than the declared ${current}"
fi
! git rev-parse -q --verify "refs/tags/${tag}" >/dev/null ||
    die "tag ${tag} already exists locally"
python3 scripts/roll_changelog.py "$version" --check

# the tag message is the release notes GitHub shows, so it defaults to the entry
if [ -z "$message" ]; then
    message="Release ${version}

$(python3 scripts/roll_changelog.py "$version" --body)"
fi

for remote in "${REMOTES[@]}"; do
    step "Checking ${remote}"
    git fetch --quiet "$remote" "$RELEASE_BRANCH"
    [ "$(git rev-parse HEAD)" = "$(git rev-parse FETCH_HEAD)" ] ||
        die "${RELEASE_BRANCH} differs from ${remote}/${RELEASE_BRANCH}, pull or push first"
    [ -z "$(git ls-remote --tags "$remote" "refs/tags/${tag}")" ] ||
        die "tag ${tag} already exists on ${remote}"
done

committed=false
cleanup() { $committed || git checkout --quiet -- pyproject.toml uv.lock CHANGELOG.md; }
trap cleanup EXIT INT

step "Bumping ${current} to ${version}"
sed -i "s/^version = \"${current}\"$/version = \"${version}\"/" pyproject.toml
grep -q "^version = \"${version}\"$" pyproject.toml || die "the version bump did not apply"
uv lock --quiet

step "Rolling the changelog"
python3 scripts/roll_changelog.py "$version"

step "Replaying the checks CI runs"
uv sync --quiet
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q

step "Committing and tagging"
git commit --gpg-sign --quiet -m "chore(release): ${version}" \
    -- pyproject.toml uv.lock CHANGELOG.md
committed=true
# git tag defaults to --cleanup=strip, which would eat the ### headings
git tag --sign --cleanup=whitespace -m "$message" "$tag"
git --no-pager show --no-patch --format='%h %s [signature %G?]' HEAD

if ! $assume_yes; then
    printf '\nPush %s and %s to %s? [y/N] ' "$RELEASE_BRANCH" "$tag" "${REMOTES[*]}"
    read -r answer
    case "$answer" in
        [yY] | [yY][eE][sS]) ;;
        *) die "nothing pushed. To undo: git tag -d ${tag} && git reset --hard HEAD~1" ;;
    esac
fi

for remote in "${REMOTES[@]}"; do
    step "Pushing to ${remote}"
    git push "$remote" "$RELEASE_BRANCH" "$tag"
done

repo="$(git remote get-url github)"
repo="${repo%.git}"
printf '\n%s is pushed. The Release workflow is now waiting for a reviewer on the\npypi environment, and publishes once approved:\n  %s/actions\n' \
    "$tag" "$repo"
