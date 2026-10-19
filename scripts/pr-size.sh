#!/usr/bin/env bash
# Checks a pull request against CONTRIBUTING.md: branch named type/short-description,
# fewer than MAX_LINES changed lines and fewer than MAX_FILES files. Generated files
# (lockfiles, OpenAPI types) and images do not count.
# Locally: BASE=origin/main HEAD=HEAD BRANCH=$(git branch --show-current) scripts/pr-size.sh
set -euo pipefail

MAX_LINES=${MAX_LINES:-500}
MAX_FILES=${MAX_FILES:-100}
IGNORED='(^|/)(pnpm-lock\.yaml|uv\.lock|openapi\.json|schema\.d\.ts|tsconfig\.tsbuildinfo)$|^docs/images/|^LICENSE$'
failed=0

if [[ ! "$BRANCH" =~ ^(feat|minor|fix|refactor|docs)/[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "::error::Branch '$BRANCH' should be named type/short-description, with type one of feat, minor, fix, refactor or docs (e.g. fix/burndown-backdated-sprint)."
  failed=1
fi

stats=$(git diff --numstat "$BASE...$HEAD" | grep -Ev "$(printf '\t')($IGNORED)" || true)
files=$(printf '%s' "$stats" | grep -c . || true)
# Binary files show "-" instead of line counts.
lines=$(printf '%s\n' "$stats" | awk '$1 != "-" { n += $1 + $2 } END { print n + 0 }')

echo "Counted $files files and $lines changed lines (limits: < $MAX_FILES files, < $MAX_LINES lines)."
if (( lines >= MAX_LINES )); then
  echo "::error::This PR changes $lines lines. Keep PRs under $MAX_LINES: split the work into smaller PRs that each do one thing (see CONTRIBUTING.md)."
  failed=1
fi
if (( files >= MAX_FILES )); then
  echo "::error::This PR touches $files files. Keep PRs under $MAX_FILES files (see CONTRIBUTING.md)."
  failed=1
fi
exit $failed
