#!/bin/bash

set -e
if [ "$1" == "dev" ]; then
  echo "Running migrations..."
  uv run alembic upgrade head
fi

PORT=${PORT:-10000}

echo "Starting application..."
if [ "$1" == "api" ]; then
  echo "Starting api service on port $PORT..."
  exec /opt/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
fi

if [ "$1" == "api-websocket" ]; then
    echo "Starting websocket service on port $PORT..."
    exec /opt/venv/bin/python -m uvicorn app.main_ws:app --host 0.0.0.0 --port $PORT
fi