#!/bin/bash
# =================================================================
# Generate requirements.lock from the live Docker image.
#
# This produces a fully-pinned (==) lock file that makes builds
# 100% reproducible. Run this after any intentional dep upgrade.
#
# Usage:
#   bash scripts/generate_requirements_lock.sh
#
# Output:
#   requirements.lock  (commit this file)
#
# In the Dockerfile, swap:
#   pip install -r requirements.txt
# for:
#   pip install -r requirements.lock
# to enforce the exact lock on every build.
# =================================================================

set -euo pipefail

IMAGE="${1:-jarvismax-jarvis:latest}"
LOCKFILE="requirements.lock"

echo "[generate_lock] Using image: $IMAGE"

docker run --rm "$IMAGE" pip freeze \
  | grep -v '^-e' \
  | grep -v '^#' \
  > "$LOCKFILE"

echo "[generate_lock] Written: $LOCKFILE ($(wc -l < "$LOCKFILE") packages)"
echo "[generate_lock] Commit this file to freeze the build."
