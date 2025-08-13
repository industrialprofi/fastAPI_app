#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h postgres -p 5432 -U ai_user > /dev/null 2>&1; do
  sleep 1
done

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting FastAPI app..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
