#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
fi

python manage.py makemigrations accounts listings managed_services partners support_center ai_listing --noinput
python manage.py migrate --noinput
python manage.py ensure_v118_schema
python manage.py ensure_v119_schema
python manage.py ensure_v120_schema
python manage.py backfill_image_fingerprints --limit 5000
python manage.py seed_categories
python manage.py rebuild_listing_matches --limit 500
python manage.py collectstatic --noinput
python manage.py check

echo "İlan Şehri v1.20.0 Codespaces kurulumu tamamlandı."
