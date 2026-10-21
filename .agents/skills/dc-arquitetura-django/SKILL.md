---
name: dc-arquitetura-django
description: Definição e manutenção da arquitetura do backend Django: apps de domínio, camadas, padrões e decisões arquiteturais.
---

# Dc Arquitetura Django

**Quando usar:** Ao criar o projeto Django, adicionar apps, modelar domínios ou tomar decisões estruturais.


## Arquitetura-alvo
Monólito modular (NÃO microserviços): Django + DRF + PostgreSQL, apps de domínio em `apps/`.

## Estrutura
```
backend/
  manage.py
  config/          # settings, urls, asgi, wsgi
  apps/
    core/          # funcionalidades compartilhadas (não vire depósito de regras)
    accounts/      # usuário customizado, grupos, permissões
    tenants/       # estabelecimento (preparar isolamento multiempresa)
    catalog/       # categorias, produtos, sabores, tamanhos, bordas, adicionais
    pricing/       # regras de preço: sabor mais caro, bordas, promoções
    customers/     # clientes e endereços
    orders/        # pedidos, itens, snapshots, histórico de status
    delivery/      # cidades, bairros, taxas, retirada
    payments/      # registro do pagamento (sem gateway na v1)
    promotions/    # cupons e descontos
    inventory/     # estoque (apenas o necessário na v1)
    employees/     # funções operacionais (sem 2º sistema de auth)
    reporting/     # indicadores consolidados
    audit/         # trilha de auditoria
  tests/
  requirements/
  docs/
```

## Regras arquiteturais
- Regras de negócio em **camada de domínio** (funções/serviços testáveis), NÃO em views, serializers ou componentes visuais.
- Um tenant nunca confia em ID enviado pelo cliente — sempre verificar autorização server-side.
- Não criar apps vazios "para o futuro". Criar quando houver necessidade real.
- Não adicionar Celery, Redis, microserviços sem necessidade demonstrada.
- Registrar decisões em `docs/adr/` (Architecture Decision Records).
