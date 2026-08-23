#!/bin/bash
set -e

echo "Waiting for MariaDB..."

# We don't have netcat, so we can just use python to test the port or sleep.
# A simple python script to check if port 3306 on 'db' is open:
python -c '
import socket
import time
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect(("db", 3306))
        s.close()
        break
    except socket.error:
        time.sleep(1)
'

echo "MariaDB started"

# If the command starts with celery, skip migrations to prevent race conditions
if [ "$1" = "celery" ]; then
    echo "Starting Celery worker (skipping migrations)..."
    exec "$@"
fi

echo "Applying database migrations..."
python manage.py migrate

echo "Checking if taxonomy is already seeded..."
if ! python manage.py shell -c "from taxonomy.models import TaxonomyCategory; import sys; sys.exit(0 if TaxonomyCategory.objects.exists() else 1)"; then
    echo "Seeding taxonomy data for the first time..."
    if [ -d "data/taxonomy_data" ]; then
        python manage.py import_shopify_taxonomy data/taxonomy_data || true
    fi
else
    echo "Taxonomy already exists! Skipping slow import."
fi

echo "Starting server..."
exec "$@"
