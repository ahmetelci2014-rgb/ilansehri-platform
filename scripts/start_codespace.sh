#!/usr/bin/env bash
set -euo pipefail

# Codespaces geliştirme ortamında yeni model değişikliklerini hazırla.

# v0.6 güvenli yayın akışı: yeni ilanlar moderasyon kuyruğuna girer.
if [ -f .env ]; then
  if grep -q '^AUTO_PUBLISH_LISTINGS=' .env; then
    sed -i 's/^AUTO_PUBLISH_LISTINGS=.*/AUTO_PUBLISH_LISTINGS=False/' .env
  else
    printf '\nAUTO_PUBLISH_LISTINGS=False\n' >> .env
  fi
fi
python manage.py makemigrations accounts listings managed_services partners --noinput
python manage.py migrate --noinput

if pgrep -f "python manage.py runserver 0.0.0.0:8000" >/dev/null 2>&1; then
  echo "İlan Şehri sunucusu zaten çalışıyor."
  exit 0
fi

nohup python manage.py runserver 0.0.0.0:8000 > /tmp/ilansehri-django.log 2>&1 &
echo "İlan Şehri v0.6 başlatıldı: port 8000"
