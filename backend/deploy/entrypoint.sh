#!/bin/sh
# Ao ligar o container: aplica migrações, garante os dados iniciais e sobe o servidor.
set -e

python manage.py migrate --noinput
# Só cria o que falta (cardápio, bairros, horários): não sobrescreve o que foi editado no painel
python manage.py import_legacy_data

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 60 \
    --access-logfile - \
    --forwarded-allow-ips "*"
