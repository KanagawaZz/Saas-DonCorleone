---
name: dc-preservacao-frontend
description: Preservação da identidade visual e dos fluxos do frontend Don Corleone durante a migração para a API.
---

# Dc Preservacao Frontend

**Quando usar:** Sempre que tocar em qualquer arquivo do frontend (JS, CSS, assets, animações).


## Regra absoluta
A identidade visual é **intocável** sem autorização explícita.

## Lista protegida
- GSAP, Lenis, Three.js e todas as animações.
- Tipografia (Fontsource), cores, espaçamentos, tokens de design.
- Ordens de seção, responsividade, efeitos 3D, identidade visual.
- PWA e service worker existentes.

## Proibições
- NÃO trocar Vanilla JS por React/Vue sem justificativa técnica e aprovação.
- NÃO simplificar layout para acelerar migração.
- NÃO substituir arquivos inteiros quando uma alteração localizada basta.
- NÃO apagar código funcional sem demonstrar necessidade.

## Procedimento antes de editar
1. Inspecionar o contexto do arquivo e suas dependências.
2. Executar o projeto e registrar baseline (capturas se possível).
3. Fazer mudança mínima, coerente e verificável.
4. Reexecutar e comparar desktop + mobile.
