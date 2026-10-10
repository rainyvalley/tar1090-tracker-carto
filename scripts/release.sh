#!/bin/bash

# Release script for Tar1090 Aircraft Tracker
# Usage: ./scripts/release.sh <version> [summary]
#
# Moves everything under "## [Unreleased]" in both CHANGELOG.md files into a
# new "## [<version>] - <date>" section (add categorised entries under
# Unreleased before releasing), bumps tar1090/config.yaml, commits, tags and
# pushes main and the tag. The optional summary becomes the first line of the
# new section and of the commit message.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <version> [summary]"
    echo "Example: $0 1.0.4 'Added new feature X'"
    exit 1
fi

VERSION=$1
SUMMARY=${2:-}
CHANGELOGS=(CHANGELOG.md tar1090/CHANGELOG.md)
FILES=(tar1090/config.yaml "${CHANGELOGS[@]}")

if [[ ! $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Version must look like 1.2.3, got: $VERSION"
    exit 1
fi

cd "$(git rev-parse --show-toplevel)"

if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
    echo "❌ Releases are made from main; check it out first."
    exit 1
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "❌ Working tree has uncommitted changes; commit or stash them first."
    exit 1
fi
if git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null; then
    echo "❌ Tag v$VERSION already exists."
    exit 1
fi
for f in "${CHANGELOGS[@]}"; do
    if ! grep -q '^## \[Unreleased\]' "$f"; then
        echo "❌ $f has no '## [Unreleased]' heading."
        exit 1
    fi
done

echo "🚀 Preparing release $VERSION..."

# Update version in config.yaml (temp file instead of sed -i: portable, no .bak)
echo "📝 Updating version in config.yaml..."
tmp=$(mktemp)
sed "s/^version: \".*\"/version: \"$VERSION\"/" tar1090/config.yaml > "$tmp"
cat "$tmp" > tar1090/config.yaml
rm -f "$tmp"

# Turn the Unreleased section into the new release section
DATE=$(date +%Y-%m-%d)
for f in "${CHANGELOGS[@]}"; do
    echo "📋 Updating $f..."
    tmp=$(mktemp)
    awk -v heading="## [$VERSION] - $DATE" -v summary="$SUMMARY" '
        !done && /^## \[Unreleased\]/ {
            print; print ""; print heading
            if (summary != "") { print ""; print summary }
            done = 1; next
        }
        { print }
    ' "$f" > "$tmp"
    cat "$tmp" > "$f"
    rm -f "$tmp"
done

# Git operations: stage only the files this script changed
echo "📦 Committing changes..."
git add -- "${FILES[@]}"
git commit -m "🔖 Release version $VERSION

${SUMMARY:-Version $VERSION release}"

echo "🏷️  Creating git tag..."
git tag -a "v$VERSION" -m "Release version $VERSION"

echo "⬆️  Pushing to remote..."
git push origin HEAD:main
git push origin "v$VERSION"

echo "✅ Release $VERSION completed!"
REPO_URL=$(git remote get-url origin | sed -e 's#^git@github.com:#https://github.com/#' -e 's#\.git$##')
echo "🌐 Check: $REPO_URL/releases"
