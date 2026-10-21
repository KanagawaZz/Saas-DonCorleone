---
name: dc-testes-qualidade
description: Estratégia e implementação de testes: unitários, integração da API e E2E dos fluxos críticos.
---

# Dc Testes Qualidade

**Quando usar:** Ao escrever qualquer regra de negócio, endpoint ou fluxo de compra.


## Pirâmide
- **Unitários**: pricing (sabor mais caro, bordas, adicionais, tamanhos), cupons, taxas, cálculo de total, pedido mínimo, geração de código de pedido.
- **Integração (API)**: criação de pedido válido/inválido, preço adulterado rejeitado, produto inativo, duplicata bloqueada, transições de status, permissões.
- **E2E (frontend)**: carregar catálogo via API, personalizar pizza, carrinho, checkout, erro de rede, WhatsApp, mobile, PWA.

## Matriz mínima de segurança
- Anônimo não acessa rotas privadas.
- Funcionário sem permissão não executa ação restrita.
- Tenant A não acessa dados do tenant B.
- Rotas públicas não vazam dados privados.

## Regras
- Nunca declarar teste aprovado sem executá-lo.
- Nunca inventar resultado de teste.
- Dados de produção reais NUNCA em testes sem autorização.
- Rodar: `python manage.py test` + testes do frontend antes de qualquer fase ser dada como concluída.
