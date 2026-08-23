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

echo "Applying database migrations..."
python manage.py migrate

echo "Seeding taxonomy data (this is idempotent)..."
# In case the JSON files aren't physically present in the volume immediately or it's a first run
if [ -d "data/taxonomy_data" ]; then
    python manage.py import_shopify_taxonomy data/taxonomy_data || true
fi

echo "Starting server..."
exec "$@"
