---
name: dc-seguranca
description: Segurança da aplicação: autenticação, autorização, proteções web e LGPD.
---

# Dc Seguranca

**Quando usar:** Em toda feature que envolva login, permissões, dados pessoais, uploads ou endpoints.


## Checklist obrigatório
- Credenciais e segredos SOMENTE em variáveis de ambiente; nunca no repositório.
- Auth: sistema nativo do Django; senhas nunca em texto plano; limitação de tentativas de login.
- Autorização verificada **sempre no backend** — o frontend nunca é autoridade.
- CSRF conforme o mecanismo de sessão/tokens; CORS restrito ao domínio do frontend.
- Proteção contra SQL injection (ORM/parametrizado) e XSS (escapar saída, sanitizar).
- Uploads de imagem: tipos permitidos, limite de tamanho, armazenamento fora de pasta pública de código.
- Rate limiting em endpoints sensíveis (login, criação de pedido).
- Logs sem segredos nem dados pessoais desnecessários.
- LGPD: coletar só o necessário (nome, telefone, endereço), transparência, e política de retenção/exclusão.

## Multi-tenant
Testes devem provar que usuário do estabelecimento A não lê/escreve dados do B.
