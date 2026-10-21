# Don Corleone — instruções para assistentes de IA

Sistema de pedidos para pizzaria (com plano de virar SaaS para outras): site do cliente, painel do dono, app do entregador com localização, WhatsApp automático.

## Primeiro passo numa máquina nova
Siga [docs/INSTALACAO-LOCAL.md](docs/INSTALACAO-LOCAL.md) na ordem, conferindo o resultado esperado de cada etapa. Produção (servidor): [docs/DEPLOY.md](docs/DEPLOY.md).

## Mapa do projeto
| Pasta | O que é |
|---|---|
| `src/` | Site do cliente (Vite, JavaScript puro). Dados iniciais em `src/data/` |
| `backend/config/settings/` | `base.py`, `local.py` (DEBUG, SQLite), `production.py` (PostgreSQL, HTTPS) |
| `backend/apps/orders/` | Pedidos; regras de status em `services.py` |
| `backend/apps/painel/` | Painel do dono (templates Django), app do entregador (`views/app_entregador.py`, rotas em `urls_entregador.py`) |
| `backend/apps/delivery/` | Bairros, horários, configurações, funcionários, vales, localização (`tracking.py`) |
| `backend/apps/integrations/evolution.py` | WhatsApp (Evolution API v2) |
| `backend/apps/core/` | Base comum: tratamento de erros (`errors.py`, `middleware.py`), comando `ocorrencia`, `import_legacy_data` |
| `docker-compose.yml` | Só o WhatsApp para desenvolvimento local |
| `docker-compose.prod.yml`, `Dockerfile.site`, `backend/Dockerfile`, `backend/deploy/` | Produção (Caddy + Django + PostgreSQL + Evolution) |
| `.agents/skills/` | Guias por área do projeto |

## Comandos
- Testes: `cd backend; ..\.venv\Scripts\python.exe manage.py test apps` (precisam passar antes de qualquer commit)
- Migrações: `.venv\Scripts\python.exe backend\manage.py makemigrations` / `migrate`
- Ligar tudo no Windows: `iniciar.cmd`
- Detalhes de um erro em produção: `python manage.py ocorrencia ERR-DDMM-XXXX`

## Regras
- Textos para o usuário em **português do Brasil**; código, nomes e comentários em inglês, seguindo o estilo do arquivo ao redor.
- Nunca faça commit de `.env`, `.env.production`, `backend/db.sqlite3`, `backend/media/`.
- Migrações: só aditivas. Não desfaça migrações já aplicadas (`migrate app 000X` apaga tabelas).
- Dependências Python: `backend/requirements/base.txt` (todas as máquinas) e `production.txt` (servidor). Não crie outro `requirements.txt`.
- Integração com Traccar Client: o endpoint `/entregador/localizacao/` responde sempre 200, porque o app reenviaria para sempre uma posição recusada.
- Windows: PowerShell 5.1 (sem `&&`); scripts `.ps1` com acento precisam de UTF-8 com BOM.
