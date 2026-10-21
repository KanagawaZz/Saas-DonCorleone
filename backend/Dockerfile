# Backend Don Corleone (painel, API, app do entregador) para produção.
# Build a partir da raiz do repositório: o comando import_legacy_data lê src/data do site.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /srv/backend

COPY backend/requirements/ requirements/
RUN pip install -r requirements/production.txt

COPY backend/ .
COPY src/data/ /srv/src/data/

# Arquivos estáticos do painel/admin vão para a imagem (servidos pelo WhiteNoise).
# As variáveis abaixo só existem durante o build: as de verdade vêm do .env no servidor.
RUN DJANGO_SECRET_KEY=build-only ALLOWED_HOSTS=build DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /srv/backend/media /srv/cache \
    && chown -R app:app /srv/backend/media /srv/cache
USER app

EXPOSE 8000
ENTRYPOINT ["sh", "/srv/backend/deploy/entrypoint.sh"]
