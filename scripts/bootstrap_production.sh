#!/usr/bin/env bash
set -euo pipefail

# MVP paketinde migration dosyaları kurulum anında üretilir.
# Canlı sürüm sabitlendikten sonra üretilen migrationların repoya alınması önerilir.
python manage.py makemigrations accounts listings managed_services partners support_center ai_listing --noinput
python manage.py migrate --noinput
python manage.py ensure_v118_schema
python manage.py ensure_v119_schema
python manage.py backfill_image_fingerprints --limit 5000
python manage.py seed_categories
python manage.py marketplace_maintenance
python manage.py rebuild_listing_matches --limit 2000
python manage.py collectstatic --noinput
python manage.py check --deploy
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-3}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
