---
name: dc-painel-admin
description: Construção do painel administrativo operacional (além do Django Admin) e gestão operacional.
---

# Dc Painel Admin

**Quando usar:** Ao implementar dashboard, telas de pedidos, cardápio, clientes, entregas e configurações.


## Princípio
Django Admin = uso interno/configuração. O painel operacional é a ferramenta do dia a dia do proprietário.

## Requisitos de UX do painel
- Identidade sofisticada e coerente com Don Corleone (sem copiar a landing page).
- Sidebar + cabeçalho + indicadores; tarefas frequentes em poucos passos.
- Tabelas funcionais, formulários organizados, estados vazios úteis, loading states.
- Confirmação em ações destrutivas; feedback claro de sucesso/erro.
- Responsivo e navegável por teclado; contraste e legibilidade.

## Módulos por prioridade (MVP primeiro)
1. Dashboard (pedidos de hoje, pendentes, ticket médio, avisos).
2. Pedidos (lista/quadro por status, filtros, detalhe completo, ações autorizadas).
3. Cardápio (CRUD de produtos, sabores, preços, disponibilidade, imagens).
4. Entregas (bairros, taxas, ativação).
5. Clientes (histórico, endereços).
6. Configurações (horários, pedido mínimo, WhatsApp, PIX público).

## Regras
- Todo número vem do banco, respeitando filtros de período.
- Diferenciar valor registrado, pago e faturamento — nunca apresentar um como outro.
- Mudança em configurações deve refletir no frontend SEM recompilação.
