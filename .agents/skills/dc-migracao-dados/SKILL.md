---
name: dc-migracao-dados
description: Importação idempotente dos dados legados do frontend (src/data/*.json e configurações em JS) para o banco Django via comando import_legacy_data.
---

# Dc Migracao Dados

**Quando usar:** Ao alterar `src/data/cardapio.json`, `src/data/bairros.json`, configurações da loja, ou o comando `import_legacy_data`; ao popular um banco novo (dev, staging, produção).

## Onde fica
- Comando: `backend/apps/core/management/commands/import_legacy_data.py`
- Execução: `python manage.py import_legacy_data` (a partir de `backend/`)
- Fontes: `src/data/cardapio.json` (categorias e itens), `src/data/bairros.json` (zonas de entrega); tenant, horários, bordas e configurações da loja estão fixos no próprio comando.

## Regras
- **Idempotente sempre:** usar `update_or_create` com chave natural (`tenant` + `slug`, `tenant` + `weekday`, `tenant` + `city` + `neighborhood`, `product` + `size_id`). Rodar duas vezes não pode duplicar nada.
- **Tudo pertence a um tenant** (`don-corleone`). Nunca criar registro de negócio sem `tenant` (ver dc-saas-multiempresa).
- **Dinheiro em `Decimal`**, convertido via `Decimal(str(valor))` — nunca direto de `float`.
- O `slug` vem do `id` do JSON legado; não mudar ids no JSON sem migrar os registros existentes, senão o import cria duplicados e deixa os antigos órfãos.
- Itens removidos do JSON **não** são apagados pelo import; desativar manualmente (`is_active` / `is_available = False`) para preservar histórico de pedidos.
- Dados de marca (nome, textos) devem seguir a identidade atual: "Pizzaria & Esfiharia", sem menções a forno a lenha.

## Ao alterar
1. Conferir se os campos novos do JSON têm destino no model (ver dc-modelagem-banco); dados sem campo próprio vão para `extra_details` só se forem informativos.
2. Rodar o import duas vezes num banco limpo e confirmar que as contagens não mudam na segunda execução.
3. Conferir preços de pizza por tamanho (pequena/média/grande) contra o frontend antes de publicar (ver dc-catalogo-precificacao).
4. Cobrir o comando com teste que executa `call_command("import_legacy_data")` duas vezes (ver dc-testes-qualidade).
