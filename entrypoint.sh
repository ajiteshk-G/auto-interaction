#!/bin/bash
set -e

PORT=${PORT:-8080}
echo "Starting Mahindra Omnichannel Backend on 0.0.0.0:8000..."
cd /app/backend
PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Waiting for backend to become healthy on port 8000..."
for i in {1..20}; do
  if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
    echo "Backend is healthy!"
    break
  fi
  sleep 0.5
done

echo "Starting Next.js Frontend on 0.0.0.0:${PORT}..."
if [ -f /app/frontend/server.js ]; then
  cd /app/frontend
  PORT=${PORT} HOSTNAME="0.0.0.0" node server.js &
elif [ -f /app/frontend/app/frontend/server.js ]; then
  mkdir -p /app/frontend/app/frontend/.next /app/frontend/app/frontend/public
  cp -rn /app/frontend/.next/static /app/frontend/app/frontend/.next/ 2>/dev/null || true
  cp -rn /app/frontend/public /app/frontend/app/frontend/ 2>/dev/null || true
  cd /app/frontend/app/frontend
  PORT=${PORT} HOSTNAME="0.0.0.0" node server.js &
else
  SERVER_JS=$(find /app/frontend -name server.js | head -n 1)
  if [ -n "$SERVER_JS" ]; then
    SERVER_DIR=$(dirname "$SERVER_JS")
    mkdir -p "$SERVER_DIR/.next"
    cp -rn /app/frontend/.next/static "$SERVER_DIR/.next/" 2>/dev/null || true
    cp -rn /app/frontend/public "$SERVER_DIR/" 2>/dev/null || true
    cd "$SERVER_DIR"
    PORT=${PORT} HOSTNAME="0.0.0.0" node server.js &
  else
    echo "ERROR: server.js not found!"
    exit 1
  fi
fi
FRONTEND_PID=$!

wait -n $BACKEND_PID $FRONTEND_PID

