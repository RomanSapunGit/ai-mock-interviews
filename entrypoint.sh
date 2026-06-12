#!/bin/bash

set -e

PORT=${PORT:-10000}

case "$1" in
  api)
    echo "Running migrations..."
    /opt/venv/bin/python -m alembic upgrade head
    echo "Starting api service on port $PORT..."
    exec /opt/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
    ;;
  *)
    echo "Unknown command: '$1' (expected 'api')" >&2
    exit 1
    ;;
esac
