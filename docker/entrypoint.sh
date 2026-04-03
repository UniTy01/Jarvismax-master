#!/bin/bash
# Entrypoint: ensure runtime data dirs exist before starting the app.
# Needed because ./:/app bind-mount hides dirs created during docker build.
set -e

mkdir -p \
    /app/data/modules \
    /app/data/mcp \
    /app/data/skills \
    /app/data/tools \
    /app/data/playbooks \
    /app/data/cognitive_events

chmod -R 777 /app/data 2>/dev/null || true

exec "$@"
