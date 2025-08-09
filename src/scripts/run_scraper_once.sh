#!/usr/bin/env bash
set -euo pipefail

cd /app/src  # Change to src directory
python webScraper.py &
APP_PID=$!

echo "Waiting for backend..."
for i in {1..60}; do
  if curl -fsS http://127.0.0.1:5000/api/status >/dev/null 2>&1; then break; fi
  sleep 1
done

echo "Triggering refresh..."
curl -fsS http://127.0.0.1:5000/api/refresh >/dev/null

echo "Waiting for artifacts..."
for i in {1..120}; do
  [[ -f "/app/src/pokemon_data.json" ]] && break  # Update path
  sleep 1
done

kill ${APP_PID} || true
sleep 2
kill -9 ${APP_PID} || true

python /app/src/scripts/upload_to_s3.py  # Update path