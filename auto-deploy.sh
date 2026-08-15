#!/bin/bash
# Polls origin/main and deploys only when a new commit has landed.
# Meant to be invoked periodically (cron or a systemd timer) -- see
# deploy-timer/ for a systemd-timer alternative that doesn't require
# installing the cron package.
#
# Not installed/scheduled by default -- this script only runs when
# something (cron, a systemd timer, or a human) actually invokes it.
set -euo pipefail
cd "$(dirname "$0")"

LOCAL=$(git rev-parse HEAD)
git fetch origin main --quiet
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "$(date -Iseconds) no new commits on origin/main ($LOCAL), skipping deploy"
    exit 0
fi

echo "$(date -Iseconds) new commit on origin/main ($LOCAL -> $REMOTE), deploying"
./deploy.sh
