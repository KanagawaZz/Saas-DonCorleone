---
name: dc-catalogo-precificacao
description: Implementação e manutenção do catálogo (pizzas personalizáveis vs. produtos simples) e das regras de precificação no backend.
---

# Dc Catalogo Precificacao

**Quando usar:** Ao trabalhar em models, serializers ou endpoints de catálogo, sabores, tamanhos, bordas, adicionais e cálculo de preço.


## Regras confirmadas (validar no código legado)
- Cobrança pelo **sabor mais caro** em pizzas com múltiplos sabores.
- Bordas recheadas como adicional com preço por tamanho.
- Preços por tamanho (ex.: broto, média, grande, família).
- Pedido mínimo documentado: R$ 22,00 — confirmar valor real no código.

## Modelagem
- Diferenciar **produto personalizável** (pizza: tamanho + N sabores + borda) de **produto simples** (bebida, sobremesa, esfiha). Não usar campo de texto genérico para características.
- `ProductBase` comuns; especializações via composição, não via um mega-modelo.

## Pricing como domínio
- Funções puras e testáveis: `calcular_preco_pizza(tamanho, sabores, borda, adicionais)`, `aplicar_cupom(...)`.
- O frontend envia a intenção; o **servidor recalcula tudo**. Preço vindo do navegador nunca é aceito como verdade.
- Endpoint `/api/v1/pricing/simulate/` para o frontend exibir preço ao vivo.
