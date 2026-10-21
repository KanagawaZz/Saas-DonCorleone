---
name: dc-api-rest
description: Construção da API REST com Django REST Framework: versionamento, rotas públicas vs. administrativas, validação e documentação.
---

# Dc Api Rest

**Quando usar:** Ao criar views, serializers, routers, permissões ou endpoints.


## Convenções
- Prefixo versionado: `/api/v1/`.
- Rotas **públicas** (somente leitura): catálogo, configurações da unidade, horários/status, bairros/taxas, simulação de preço, criação de pedido, validação de cupom.
- Rotas **administrativas**: pedidos, clientes, estoque, funcionários, relatórios, configurações — exigem auth + permissão por perfil.
- NUNCA expor dados de clientes, relatórios ou funcionários em rotas públicas.

## Qualidade
- Validadores de entrada rigorosos; respostas de erro consistentes (`{"detail": ..., "errors": {...}}`).
- Paginação em listas administrativas.
- Transações (`transaction.atomic`) em operações multi-etapa (criar pedido, aplicar cupom, registrar pagamento).
- Documentar endpoints em `docs/api/` (parâmetros, respostas, erros).

## Idempotência
Criação de pedido deve aceitar chave de idempotência (ex.: UUID gerado no frontend no início do checkout) para não duplicar em reenvios/retry.
