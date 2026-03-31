#!/usr/bin/env bash
# JARVIS MAX — Arrêt
echo "[Jarvis] Arrêt de la stack..."
docker compose down
echo "[✓] Stack arrêtée. Les données sont persistées dans les volumes Docker."
