---
name: dc-modelagem-banco
description: Modelagem do banco relacional PostgreSQL: entidades, relacionamentos, snapshots históricos, integridade e precisão monetária.
---

# Dc Modelagem Banco

**Quando usar:** Ao criar ou alterar models.py, migrations ou o diagrama ER.


## Princípios
- Dinheiro: `DecimalField`, NUNCA FloatField.
- Fuso: America/Cuiaba (USE_TZ=True).
- Exclusão de cadastros: preferir inativação (is_active) — NUNCA destruir histórico comercial.
- Pedidos e seus itens guardam **snapshot** dos dados usados na compra (descrição, composição, preço). Alterar o catálogo nunca altera pedidos antigos.
- Código de pedido: único, gerado/validado no servidor, resistente a concorrência (transação ou sequência).
- Chaves estrangeiras com on_delete PROTECT para dados históricos; índices em campos de consulta (status, created_at, telefone, bairro).
- Todo modelo de negócio (exceto auth puro) carrega FK para o estabelecimento (tenant).

## Entidades mínimas
Estabelecimento, Usuário, Perfil, Categoria, Produto, Sabor, Tamanho, Adicional, Borda, Preço, Cliente, Endereço, Cidade, Bairro, TaxaEntrega, Pedido, ItemPedido, ItemSabor, ItemAdicional, Pagamento, Cupom, HistoricoStatus, Estoque, MovimentoEstoque, RegistroAuditoria.

## Antes de codar
Produzir/atualizar diagrama ER em `docs/` e revisar cardinalidades. Não criar tabela sem justificar necessidade.
