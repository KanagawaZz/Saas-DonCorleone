---
name: dc-gestao-projeto
description: Gestão das fases, rastreamento de decisões e critérios de aceitação do projeto Don Corleone.
---

# Dc Gestao Projeto

**Quando usar:** Em cada mudança de fase, decisão arquitetural relevante ou entrega.


## Fases (não pular etapas)
0. Auditoria e planejamento → 1. Fundação Django → 2. Catálogo e configurações → 3. Integração com o site → 4. Pedidos e operação → 5. Painel inicial → 6. Módulos adicionais → 7. Produção → 8. Evolução SaaS.

## Em cada fase
- Registrar arquivos alterados e motivo de cada mudança relevante.
- Alterações pequenas, coerentes e verificáveis (commits atômicos).
- Manter `docs/` atualizado: README, arquitetura, ER, API, setup local, testes, migração, env vars, deploy, backup/restore, ADRs.

## Critérios de aceitação globais
- Identidade visual preservada; fluxos atuais funcionando.
- Catálogo e taxas administráveis sem editar JSON.
- Preços validados no servidor; pedidos persistidos com snapshot.
- WhatsApp disponível; painel com auth; permissões no backend.
- Testes críticos passando; documentação permite rodar o projeto.

## Nunca
- Declarar funcionalidade concluída se estiver parcial.
- Executar comando destrutivo sem autorização (git reset --hard, drop, etc.).
