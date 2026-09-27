#!/bin/bash
# Run only from a dedicated clone of the blog repository.
set -euo pipefail
export GIT_TERMINAL_PROMPT=0
cd "$(dirname "$0")/.."

if [[ "$(git branch --show-current)" != "main" ]]; then
  echo 'Sync requires the dedicated clone on main.' >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Sync stopped: the dedicated clone has local changes.' >&2
  exit 1
fi

git pull --ff-only --quiet origin main
.venv/bin/python -m pip install --disable-pip-version-check --quiet -r requirements.txt
.venv/bin/python blog.py sync
.venv/bin/python blog.py build

if ! git diff --quiet -- data/posts.json; then
  git add data/posts.json
  git -c user.name='Jibril blog sync' \
      -c user.email='nodeDevcoder@users.noreply.github.com' \
      commit -m 'Import public Substack posts'
fi
# Also retries a prior successful import whose push failed temporarily.
git push --quiet origin HEAD:main
date -u '+Public RSS sync completed at %Y-%m-%dT%H:%M:%SZ'
