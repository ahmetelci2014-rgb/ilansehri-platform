#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
fi

python manage.py makemigrations accounts listings managed_services partners --noinput
python manage.py migrate --noinput
python manage.py seed_categories
python manage.py collectstatic --noinput
python manage.py check

echo "İlan Şehri v1.9 Codespaces kurulumu tamamlandı."
