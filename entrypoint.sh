#!/bin/bash

set -e

echo "Running migrations..."
uv run alembic upgrade head

echo "Starting application..."
if [ "$1" == "api" ]; then
  echo "Starting api service..."
  exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi

if [ "$1" == "api-websocket" ]; then
    echo "Starting websocket service..."
    exec uv run uvicorn app.main_ws:app --host 0.0.0.0 --port "${PORT:-8001}" --reload
fi