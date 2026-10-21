# Colocar o Don Corleone no ar

Tudo roda em **um único servidor (VPS)**: um computador alugado num datacenter, ligado 24 horas, com internet. Nele ficam o site, o sistema e o WhatsApp.

| Endereço | O que é |
|---|---|
| `https://doncorleonepizzas.com.br` | Site onde o cliente faz o pedido |
| `https://sistema.doncorleonepizzas.com.br` | Painel, app do entregador e endereço do Traccar |

O certificado HTTPS (cadeado) é gerado e renovado sozinho pelo Caddy, o servidor web incluído. O WhatsApp (Evolution) fica só na rede interna do servidor.

Você vai precisar de duas coisas: **o domínio** e **o servidor**.

---

## Parte 1 — Contratar

### 1.1 Domínio
Registre `doncorleonepizzas.com.br` no **Registro.br** (https://registro.br). Precisa de CPF ou CNPJ, e a cobrança é anual. Alguns provedores de VPS também vendem domínio `.com.br`; se preferir tudo na mesma conta, confira no provedor.

### 1.2 Servidor (VPS)
Contrate um VPS com:
- **Datacenter em São Paulo** (mais perto dos clientes)
- **2 vCPU, 4 GB de RAM ou mais, 50 GB de disco**
- Sistema **Ubuntu 24.04** (se houver a opção "Ubuntu com Docker", melhor ainda)

Sugestão para quem está começando: **Hostinger VPS** (tem datacenter no Brasil, painel e suporte em português, pagamento em reais e terminal no navegador). Confira preço e localização na hora de contratar.

Ao terminar, anote o **IP** do servidor (quatro números, ex.: `203.0.113.10`) e a **senha do usuário root**.

---

## Parte 2 — Apontar o domínio para o servidor (DNS)

No lugar onde o domínio foi registrado (no Registro.br: domínio → **DNS** → **Editar zona**), crie três registros do tipo **A**, todos com o IP do servidor:

| Tipo | Nome | Valor |
|---|---|---|
| A | (vazio ou `@`) | IP do servidor |
| A | `www` | IP do servidor |
| A | `sistema` | IP do servidor |

Pode levar de alguns minutos a algumas horas para valer. Para conferir, no PowerShell: `nslookup sistema.doncorleonepizzas.com.br` deve mostrar o IP do servidor.

---

## Parte 3 — Enviar o código para o GitHub

No computador, na pasta do projeto:

```powershell
git add .
git commit -m "Sistema completo: painel, entregadores, vales, WhatsApp e deploy"
git push
```

Arquivos com senhas (`.env`, `.env.production`) e o banco local ficam de fora automaticamente.

---

## Parte 4 — Servidor

Acesse o servidor pelo terminal do painel do provedor ou pelo PowerShell: `ssh root@IP-DO-SERVIDOR`.

### 4.1 Preparar (uma vez)
```bash
# Docker (pule se o servidor já veio com Docker)
curl -fsSL https://get.docker.com | sh

# Firewall: acesso SSH e o site (HTTP/HTTPS)
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443 && ufw --force enable

# Código
git clone https://github.com/KanagawaZz/DonCorleone.git /opt/doncorleone
cd /opt/doncorleone
```
Se o repositório for privado, o GitHub pede usuário e um **token** (GitHub → Settings → Developer settings → Personal access tokens) no lugar da senha.

### 4.2 Configurar
```bash
cp .env.production.example .env.production
nano .env.production
```
- Confira os dois domínios e coloque o seu e-mail em `ACME_EMAIL`.
- Em `SUPPORT_WHATSAPP`, coloque o WhatsApp de quem dá suporte (DDD + número), para receber avisos de erro.
- Para cada chave e senha, rode `openssl rand -base64 48` e cole o resultado.
- Salve com `Ctrl+O`, `Enter`, `Ctrl+X`.

### 4.3 Ligar tudo
**Antes, confira que o DNS da Parte 2 já aponta para o servidor**: o certificado HTTPS só é emitido com o domínio funcionando.

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```
Na primeira vez leva alguns minutos. O sistema já sobe com o cardápio, os bairros e os horários iniciais.

### 4.4 Criar o login do dono
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec web python manage.py createsuperuser
```

### 4.5 Conferir
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
docker compose -f docker-compose.prod.yml --env-file .env.production exec web \
  python manage.py shell -c "exec(open('deploy/smoke_login.py', encoding='utf-8').read())"
```
O segundo comando deve terminar com `RESULTADO: OK`. Depois abra no navegador:
- `https://doncorleonepizzas.com.br` (site)
- `https://sistema.doncorleonepizzas.com.br/painel/` (painel)

Se o cadeado não aparecer, veja o motivo com `docker compose -f docker-compose.prod.yml --env-file .env.production logs caddy` (geralmente é o DNS que ainda não apontou).

---

## Parte 5 — Primeiros passos no sistema publicado

1. **Painel → WhatsApp**: gere o QR Code e conecte o WhatsApp da pizzaria (o do computador não vem junto).
2. **Funcionários e vales**: cadastre a equipe.
3. **Entregadores → cada entregador → Gerar link de acesso**: cada um lê o QR Code do app e o do Traccar de novo (os de teste apontavam para o computador).
4. **Configurações**: confira horários, pedido mínimo e PIX.
5. Faça um pedido de teste pelo site e acompanhe até a entrega.

---

## Dia a dia

**Atualizar** depois de mudanças no código (no servidor):
```bash
cd /opt/doncorleone
git pull
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

**Erros e suporte:** quando algo falha, quem estava usando vê uma tela amigável com um **código de ocorrência** (ex.: `ERR-2110-K7QX`), e o WhatsApp de `SUPPORT_WHATSAPP` recebe um aviso (no máximo um por tipo de erro a cada 30 minutos). Com o código em mãos:
```bash
DC="docker compose -f docker-compose.prod.yml --env-file .env.production"
$DC exec web python manage.py ocorrencia ERR-2110-K7QX             # tudo sobre a ocorrência: erro, linha do código, usuário, dados enviados
$DC exec web python manage.py ocorrencia --ultimas 20              # as mais recentes
$DC exec web python manage.py ocorrencia ERR-2110-K7QX --resolvida # marcar como resolvida
```
As ocorrências também aparecem em `https://sistema.doncorleonepizzas.com.br/admin/` (só para superusuário) e ficam guardadas por 30 dias. Senhas e tokens enviados nunca são gravados.

**Ver o registro (log) do sistema ao vivo:**
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f web
```

**Backup:** uma cópia do banco é feita por dia em `/opt/doncorleone/backups` (guarda 14 dias). Baixe de tempos em tempos para outro lugar, por exemplo do seu computador:
```powershell
scp root@IP-DO-SERVIDOR:/opt/doncorleone/backups/*.sql.gz .
```

**Restaurar um backup** (substitui todos os dados atuais pelos do dia escolhido):
```bash
DC="docker compose -f docker-compose.prod.yml --env-file .env.production"
$DC stop web
$DC exec -T db psql -U doncorleone -d doncorleone -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
gunzip -c backups/doncorleone-AAAA-MM-DD.sql.gz | $DC exec -T db psql -U doncorleone -d doncorleone
$DC start web
```
