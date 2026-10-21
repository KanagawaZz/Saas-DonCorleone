---
name: dc-infra-deploy
description: Infraestrutura: hospedagem do backend Python, PostgreSQL, mídia, backups e processo de publicação com reversão.
---

# Dc Infra Deploy

**Quando usar:** Ao preparar ambientes, fazer deploy ou configurar produção.


## Contexto
- Frontend: Cloudflare Workers (atual). Backend Django NÃO roda nesse ambiente — separar.
- Opções compatíveis com Python: Railway, Render, Fly.io, VPS (Ubuntu + Nginx + Gunicorn + Postgres gerenciado).

## Stack de produção
- Gunicorn/Uvicorn (ASGI) atrás de Nginx; HTTPS obrigatório.
- PostgreSQL gerenciado; mídia em S3-compatível (Cloudflare R2) ou volume persistente.
- `ALLOWED_HOSTS`, `DEBUG=False`, `SECRET_KEY` por env, `django-storages` para mídia.

## Checklist de publicação
- Backups automáticos do banco + teste de restauração REAL.
- Logs e monitoramento (sentry ou similar, sem segredos).
- Migrations executadas como etapa separada.
- Procedimento de reversão documentado (rollback de versão + restore).
- Checklist de segurança do Django (`manage.py check --deploy`).

## Proibições
- NÃO fazer deploy automaticamente.
- NÃO alterar DNS, domínio ou publicação atual sem autorização explícita.
