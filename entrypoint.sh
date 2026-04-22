#!/bin/bash

set -e
if [ "$1" == "dev" ]; then
  echo "Running migrations..."
  uv run alembic upgrade head
fi

echo "Starting application..."
if [ "$1" == "api" ]; then
  echo "Starting api service on port 8080..."
  exec /opt/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
fi

if [ "$1" == "api-websocket" ]; then
    echo "Starting websocket service on port 8080..."
    exec /opt/venv/bin/python -m uvicorn app.main_ws:app --host 0.0.0.0 --port 8080
fi