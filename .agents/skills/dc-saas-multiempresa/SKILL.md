---
name: dc-saas-multiempresa
description: Preparação arquitetural para multi-tenancy (várias pizzarias) SEM implementar cobrança/planos ainda.
---

# Dc Saas Multiempresa

**Quando usar:** Ao modelar qualquer dado de negócio ou revisar isolamento de dados.


## Estado atual
Don Corleone é o único tenant. Isolamento já deve existir no schema, mas NÃO implementar: assinaturas, planos, trial, marketplace, onboarding automatizado.

## Requisitos desde o início
- Todo modelo de negócio com FK para `Establishment` (tenants app).
- Querysets filtrados por tenant no backend (mixin ou manager); nunca filtrar só no frontend.
- Autorização: usuário só opera no tenant ao qual pertence (testes obrigatórios de isolamento).
- Futuro: catálogo, preços, identidade, horários, bairros, funcionários e domínio próprio por tenant.
