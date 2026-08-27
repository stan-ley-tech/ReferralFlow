#!/bin/sh
set -e

if [ "$1" = "gunicorn" ]; then
    echo "Waiting for database..."
    python manage.py wait_for_db

    echo "Applying database migrations..."
    python manage.py migrate --noinput

    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

exec "$@"
