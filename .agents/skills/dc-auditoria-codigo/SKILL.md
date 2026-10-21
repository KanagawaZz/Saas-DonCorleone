---
name: dc-auditoria-codigo
description: Auditoria técnica do repositório Don Corleone antes de qualquer mudança. Inventário de funcionalidades, regras de negócio e baseline visual.
---

# Dc Auditoria Codigo

**Quando usar:** Antes de qualquer alteração de código, migração ou nova funcionalidade.


## Objetivo
Mapear o estado real do código sem presumir nada da documentação. Toda conclusão deve ser classificada como: **CONFIRMADO NO CÓDIGO**, **IDENTIFICADO NA DOCUMENTAÇÃO**, **HIPÓTESE A VALIDAR** ou **DECISÃO PENDENTE**.

## Procedimento obrigatório
1. Mapear estrutura completa: pontos de entrada, componentes, módulos, utils, assets.
2. Identificar todas as regras comerciais: preço do sabor mais caro, pedido mínimo (R$ 22,00?), taxas por bairro, retirada, horário de corte, formas de pagamento, troco.
3. Mapear carrinho, checkout, persistência local (localStorage), geração de código de pedido e montagem da mensagem do WhatsApp.
4. Verificar PWA/service worker, Vite, dependências exatas (package.json) e versões instaladas.
5. Registrar comportamentos que DEVEM permanecer inalterados (lista protegida).
6. Executar o projeto localmente e registrar baseline (build ok, erros, console).
7. Verificar desktop e mobile (responsividade).

## Entregáveis
- Relatório de inventário funcional com classificação de cada item.
- Lista de divergências entre documentação e código.
- Lista de riscos técnicos.
- Baseline de comportamento registrada.

## Proibições
- NÃO alterar código nesta fase.
- NÃO presumir que arquivos descritos em documentos existem com esses nomes.
- NÃO esconder erros encontrados.
