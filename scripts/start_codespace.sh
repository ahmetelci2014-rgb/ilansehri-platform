#!/usr/bin/env bash
set -euo pipefail

if pgrep -f "python manage.py runserver 0.0.0.0:8000" >/dev/null 2>&1; then
  echo "İlan Şehri sunucusu zaten çalışıyor."
  exit 0
fi

nohup python manage.py runserver 0.0.0.0:8000 > /tmp/ilansehri-django.log 2>&1 &
echo "İlan Şehri başlatıldı: port 8000"
