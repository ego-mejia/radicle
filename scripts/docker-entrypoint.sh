#!/bin/sh
# Apply pending migrations, then start the app. Retries while Postgres is still booting.
set -e
attempt=0
until alembic upgrade head; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "Database not reachable after 30 attempts" >&2
    exit 1
  fi
  echo "Waiting for the database ($attempt)..." >&2
  sleep 2
done
exec "$@"
