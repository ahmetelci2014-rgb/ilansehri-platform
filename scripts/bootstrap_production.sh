#!/usr/bin/env bash
set -euo pipefail

# MVP paketinde migration dosyaları kurulum anında üretilir.
# Canlı sürüm sabitlendikten sonra üretilen migrationların repoya alınması önerilir.
python manage.py makemigrations accounts listings managed_services partners --noinput
python manage.py migrate --noinput
python manage.py seed_categories
python manage.py marketplace_maintenance
python manage.py collectstatic --noinput
python manage.py check --deploy
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-3}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
