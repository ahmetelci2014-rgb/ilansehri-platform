#!/usr/bin/env bash
set -euo pipefail

# Hosting panelindeki günlük zamanlayıcı/cron bu dosyayı günde bir kez çalıştırabilir.
# Örnek cron: 15 6 * * * /app/scripts/run_daily_maintenance.sh
cd "$(dirname "$0")/.."
python manage.py marketplace_maintenance
