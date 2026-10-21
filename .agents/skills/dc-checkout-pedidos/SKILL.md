---
name: dc-checkout-pedidos
description: Fluxo completo de pedido: validação server-side, idempotência, snapshot, códigos e encaminhamento ao WhatsApp.
---

# Dc Checkout Pedidos

**Quando usar:** Ao implementar ou alterar o checkout, criação de pedidos, status ou integração com WhatsApp.


## Fluxo-alvo
1. Cliente monta carrinho (frontend, localStorage).
2. Backend valida: produtos ativos, preços recalculados, taxa por bairro (servidor), pedido mínimo, horário de funcionamento, cupom.
3. Pedido persistido em transação com **snapshot** dos itens.
4. Backend retorna código legível + dados de confirmação.
5. Frontend mostra confirmação e oferece abrir WhatsApp com mensagem formatada.

## Regras críticas
- Se a persistência falhar → NÃO mostrar confirmação de pedido registrado.
- Se o WhatsApp falhar → o pedido registrado NÃO desaparece.
- Distinguir: **registrado** vs **mensagem aberta no WhatsApp** vs **aceito pela equipe** vs **em produção**.
- Código de pedido gerado no servidor (não confiar no navegador).
- Idempotency-Key no POST de criação.

## Estados propostos
Novo → Em confirmação → Confirmado → Em preparação → Pronto → Saiu para entrega → Concluído; Cancelado como ramificação. Definir transições permitidas e perfis autorizados (registrar quem alterou).
