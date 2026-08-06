#!/usr/bin/env bash
set -euo pipefail

RELEASE_VERSION="$(tr -d '\r\n' < VERSION)"

if [ ! -f .env ]; then
  cp .env.example .env
fi

# Geliştirme önizlemesinde yeni ilanlar moderasyon kuyruğuna girer.
if grep -q '^AUTO_PUBLISH_LISTINGS=' .env; then
  sed -i 's/^AUTO_PUBLISH_LISTINGS=.*/AUTO_PUBLISH_LISTINGS=False/' .env
else
  printf '\nAUTO_PUBLISH_LISTINGS=False\n' >> .env
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

if pgrep -f "python manage.py runserver 0.0.0.0:8000" >/dev/null 2>&1; then
  echo "İlan Şehri ${RELEASE_VERSION} sunucusu zaten çalışıyor."
  exit 0
fi

nohup python manage.py runserver 0.0.0.0:8000 > /tmp/ilansehri-django.log 2>&1 &
echo "İlan Şehri ${RELEASE_VERSION} başlatıldı: port 8000"
