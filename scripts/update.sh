#!/bin/bash
set -e
cd /opt/Jarvismax
git pull origin master

# Rebuild and restart (volume-mounted code, rebuild only if Dockerfile changed)
docker compose up -d jarvis --build

# Wait for healthy
echo "Waiting for Jarvis to start..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Jarvis is healthy!"
    exit 0
  fi
  sleep 2
done

echo "❌ Jarvis did not start within 60s"
exit 1
