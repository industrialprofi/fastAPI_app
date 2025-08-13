#!/bin/bash
set -e

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; do
  sleep 1
done

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"
