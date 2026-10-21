---
name: dc-camada-api-frontend
description: Camada de comunicação do frontend com a API Django: client central, módulos por domínio, tratamento de erros e estados.
---

# Dc Camada Api Frontend

**Quando usar:** Ao integrar o site à API ou modificar como o frontend busca dados.


## Estrutura sugerida (adaptar à estrutura real existente)
```
src/api/
  client.js      # fetch central: baseURL, headers, timeout, retry, erro padronizado
  catalog.js     # categorias, produtos, sabores, tamanhos
  delivery.js    # bairros, taxas, retirada
  pricing.js     # simulação de preço
  orders.js      # criação/consulta de pedidos
  settings.js    # configurações públicas da unidade
```

## Regras
- NENHUMA URL de API espalhada em componentes. Tudo passa por `client.js`.
- Config de ambiente via variáveis do Vite (`import.meta.env.VITE_API_URL`).
- Estados centralizados: loading / error / success com feedback ao usuário.
- Fallback: se a API falhar, comportamento degradado elegante (mensagem clara, sem crash).
- Carrinho continua em localStorage como estado temporário, mas o servidor valida tudo no checkout.
- Substituição gradual: migrar um módulo por vez (bairros → catálogo → configurações), mantendo caminho de reversão.
