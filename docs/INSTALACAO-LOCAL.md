# Rodar o projeto em outro computador (testes)

Guia para instalar o Don Corleone numa máquina nova, por exemplo o computador do trabalho, e deixar **site + painel + app do entregador** funcionando para testes. Serve para seguir à mão ou para pedir a uma IA (Claude Code, Codex, Cursor...): *"leia docs/INSTALACAO-LOCAL.md e instale o projeto nesta máquina"*.

> **Para a IA que estiver executando este guia:** siga as etapas na ordem e confira o resultado esperado de cada uma antes de seguir. Os comandos são para **Windows / PowerShell** (há equivalentes Linux/macOS no fim). Não crie nem altere arquivos versionados durante a instalação; o único arquivo novo é o `.env` (fora do git). Nunca faça commit do `.env`. Se algo falhar, consulte "Problemas conhecidos" antes de improvisar.

---

## 0. O que vai rodar

| Parte | Tecnologia | Endereço local | Obrigatório? |
|---|---|---|---|
| Sistema (painel, API, app do entregador) | Django (Python), banco SQLite | http://localhost:8000/painel/ | Sim |
| Site do cliente | Vite (Node.js) | http://localhost:3000 | Sim |
| WhatsApp automático | Evolution API no Docker | http://localhost:8081 (interno) | **Não**: sem ele, tudo funciona, só não saem as mensagens |

O banco local é um arquivo SQLite (`backend/db.sqlite3`) criado na instalação, **vazio de pedidos**: não traz os dados de outro computador.

---

## 1. Programas necessários

Confira no PowerShell. Instale o que faltar e **feche e reabra o PowerShell** depois de instalar.

| Programa | Conferir | Versão | Onde baixar |
|---|---|---|---|
| Git | `git --version` | qualquer recente | https://git-scm.com/download/win |
| Python | `py -0p` ou `python --version` | **3.12 ou 3.13** | https://www.python.org/downloads/ (marque "Add python.exe to PATH") |
| Node.js | `node --version` | **20 ou mais novo** (o projeto usa 24) | https://nodejs.org (versão LTS) |
| Docker Desktop | `docker --version` | opcional (só WhatsApp) | https://www.docker.com/products/docker-desktop/ |

Em computador de empresa sem permissão de administrador, o Docker costuma não instalar: pule-o.

---

## 2. Baixar o código

Use uma pasta de **caminho curto** (o Windows limita caminhos a 260 caracteres e algumas bibliotecas passam disso em pastas fundas):
```powershell
New-Item -ItemType Directory -Force C:\dev | Out-Null
cd C:\dev
git clone https://github.com/KanagawaZz/Saas-DonCorleone.git
cd Saas-DonCorleone
```
Se o repositório for privado, o Git pede login do GitHub (abre uma janela do navegador).

**Resultado esperado:** a pasta `Saas-DonCorleone` com `backend/`, `src/`, `package.json`, `iniciar.cmd`.

---

## 3. Python: ambiente e dependências

Na raiz do projeto:
```powershell
py -3.13 -m venv .venv        # ou: python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r backend\requirements\local.txt
```
**Resultado esperado:** termina com `Successfully installed ... Django-5.1...`.

O `.venv` é a "caixa" de bibliotecas do projeto; não precisa "ativar". Todos os comandos deste guia chamam `.venv\Scripts\python.exe` direto.

---

## 4. Arquivo de configuração `.env`

```powershell
Copy-Item .env.example .env
```
Depois gere chaves aleatórias e grave no `.env` (necessárias para o WhatsApp no Docker; inofensivo se não for usar):
```powershell
function Rand { -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 40 | ForEach-Object { [char]$_ }) }
$t = Get-Content .env -Raw
$t = $t -replace 'EVOLUTION_API_KEY=.*', "EVOLUTION_API_KEY=$(Rand)" -replace 'EVOLUTION_DB_PASSWORD=.*', "EVOLUTION_DB_PASSWORD=$(Rand)"
[IO.File]::WriteAllText("$PWD\.env", $t, (New-Object Text.UTF8Encoding($false)))
Select-String .env -Pattern 'EVOLUTION_API_URL|SITE_PUBLIC_URL'
```
**Resultado esperado:** `EVOLUTION_API_URL=http://localhost:8081` e `SITE_PUBLIC_URL=http://localhost:3000`.

---

## 5. Banco de dados, dados iniciais e login

```powershell
.venv\Scripts\python.exe backend\manage.py migrate
.venv\Scripts\python.exe backend\manage.py import_legacy_data
.venv\Scripts\python.exe backend\manage.py createsuperuser
```
- `migrate` cria o banco `backend/db.sqlite3` (termina sem erro, várias linhas `Applying ... OK`).
- `import_legacy_data` carrega cardápio, bairros e horários a partir de `src/data` (esperado: `[OK] 36 bairros`, `[OK] 67 produtos`).
- `createsuperuser` pede usuário, e-mail (pode deixar vazio) e senha: é o login do painel e do `/admin/`.

---

## 6. Conferir que o sistema está saudável (testes)

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py test apps
cd ..
```
**Resultado esperado:** `Ran 110 tests` (ou mais) e `OK`. Pode aparecer uma linha `skipped` sobre dependências de produção: é normal no computador local.

---

## 7. Site: dependências do Node

```powershell
npm ci
```
**Resultado esperado:** `added ... packages`. (Se `npm ci` reclamar do `package-lock.json`, use `npm install`.)

---

## 8. Ligar tudo

**Jeito fácil:** dois cliques em `iniciar.cmd` (ou `.\iniciar.ps1` no PowerShell). Ele abre uma janela para o sistema e outra para o site, e tenta subir o WhatsApp se o Docker estiver aberto.

**Jeito manual** (dois terminais, na raiz do projeto):
```powershell
# Terminal 1 — sistema
.venv\Scripts\python.exe backend\manage.py runserver 0.0.0.0:8000
# Terminal 2 — site
npm run dev
```
WhatsApp (opcional, com Docker Desktop aberto): `docker compose up -d`.

**Conferir:**
| Abrir | Esperado |
|---|---|
| http://localhost:3000 | Site com o cardápio carregado |
| http://localhost:8000/painel/ | Login do painel; entre com o usuário do passo 5 |
| http://localhost:8000/admin/ | Admin técnico do Django |

Teste rápido de ponta a ponta: faça um pedido de **entrega** pelo site → ele aparece em **Painel → Pedidos** → **Confirmar** → **Saiu para entrega**.

---

## 9. Testar no celular (opcional)

O celular precisa estar no **mesmo Wi-Fi** e o computador precisa aceitar conexões da rede (em empresa, isso costuma ser bloqueado).
1. Descubra o IP: `ipconfig` → "Endereço IPv4" (ex.: `192.168.0.15`). O `iniciar.ps1` já mostra no final.
2. Ligue com `iniciar.cmd` (ele já configura o site com o IP) ou, manualmente, `$env:VITE_API_URL="http://SEU-IP:8000/api/v1"; npm run dev -- --host`.
3. No primeiro uso, o Windows pergunta sobre o firewall para Python e Node: **Permitir**. Se a rede estiver como "Pública", mude para "Privada" (Configurações → Rede e Internet).
4. Abra o painel **pelo IP** (`http://SEU-IP:8000/painel/`) para gerar links e QR Codes dos entregadores: eles usam o endereço pelo qual o painel foi aberto.

---

## Problemas conhecidos

| Sintoma | Causa e solução |
|---|---|
| No passo 3: `Windows Long Path support` e depois `No module named 'django.utils'` | A pasta do projeto tem um caminho longo demais para o Windows (limite de 260 caracteres). Clone numa pasta curta, como `C:\dev\Saas-DonCorleone`, apague o `.venv` e refaça o passo 3. |
| `npm warn install-scripts` no passo 7 | Aviso das versões novas do npm. Pode ignorar: o site não depende desses scripts. |
| `py` ou `python` não é reconhecido | Python não está no PATH. Reinstale marcando "Add python.exe to PATH" ou use o caminho completo do `python.exe`. |
| `não pode ser carregado porque a execução de scripts foi desabilitada` ao rodar `iniciar.ps1` | Use `iniciar.cmd` (ele contorna a política) ou `powershell -ExecutionPolicy Bypass -File iniciar.ps1`. |
| `Error: That port is already in use` (8000) ou Vite sobe em outra porta que não 3000 | Outro programa usa a porta. Veja quem: `netstat -ano \| findstr :8000`. Feche-o, ou rode o Django em outra porta (`runserver 0.0.0.0:8010`) e o site com `$env:VITE_API_URL="http://localhost:8010/api/v1"`. |
| Site abre mas o cardápio não carrega / "O servidor demorou para responder" | O sistema (porta 8000) não está ligado, ou `VITE_API_URL` aponta para outro endereço. Ligue o Django e reinicie o `npm run dev`. |
| Tela amarela do Django com `NameError`/`ImportError` logo depois de editar código | O recarregamento automático pegou o arquivo pela metade. Salve o arquivo de novo (ou reinicie o `runserver`). |
| Docker: "Espaço insuficiente no disco" ou container reiniciando com código 139 | Disco cheio corrompe imagens. Libere espaço, apague a imagem (`docker rmi evoapicloud/evolution-api:v2.3.7`) e rode `docker compose up -d` de novo. |
| `docker compose` reclama de `EVOLUTION_API_KEY` | O `.env` não tem as chaves: refaça o passo 4. |
| WhatsApp não envia | Normal sem Docker. Com Docker: Painel → WhatsApp → gerar QR Code e conectar um número de teste. |
| Celular não acessa o computador | Rede corporativa ou firewall bloqueando. Confirme o mesmo Wi-Fi, rede "Privada" e o `runserver 0.0.0.0:8000`. Em empresa, muitas vezes não há solução: teste só no computador. |
| Um processo `runserver` aparece 4 vezes no Gerenciador de Tarefas | Normal no Windows (o Python do `.venv` e o recarregamento automático duplicam processos). É um servidor só. |

---

## Linux / macOS

Mesmos passos, trocando:
- `py -3.13 -m venv .venv` → `python3 -m venv .venv`
- `.venv\Scripts\python.exe` → `.venv/bin/python`
- Passo 4: `cp .env.example .env` e edite as duas chaves com `openssl rand -hex 20`.
- `iniciar.cmd`/`iniciar.ps1` são só para Windows: use o jeito manual do passo 8.

---

## Depois de testar

- Mudanças de código: `git add`, `git commit`, `git push` como em qualquer máquina. O `.env` e o `backend/db.sqlite3` nunca vão para o git.
- Para trazer o que foi feito no outro computador: `git pull` e, se vierem migrações novas, `.venv\Scripts\python.exe backend\manage.py migrate`.
- Produção (servidor de verdade) é outro guia: [DEPLOY.md](DEPLOY.md).
