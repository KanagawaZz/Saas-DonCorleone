# Manual e Especificação do Sistema Evoluído — Don Corleone

**Versão:** 2.0 (Backend Django Modular + API REST + Rastreio em Tempo Real + Impressão Térmica + Evolution API)  
**Unidade:** Cidade Alta, Cuiabá/MT  
**Tecnologias:** Python 3.13, Django 5.1, Django REST Framework, Vite 6, Vanilla JS, GSAP, Lenis

---

## 1. Visão Geral da Evolução

O projeto Don Corleone foi transformado de uma landing page estática para uma **plataforma gastronômica e sistema operacional comercial completo**, preservando 100% da identidade visual, animações e experiência do cliente.

---

## 2. As 8 Novas Funcionalidades Implementadas

### 1. Pedidos Centralizados no Banco de Dados
* **Como funciona:** O cliente finaliza a compra no site público e o payload é enviado para `POST /api/v1/orders/create/`.
* O backend valida os preços no servidor (sabor mais caro, bordas e adicionais), calcula a taxa de frete pelo bairro oficial e persiste o pedido com status `NOVO`.
* O código legível oficial (`DC-DDMM-XXX`) é gerado e retornado para abrir o WhatsApp e a tela de confirmação.

### 2. Clube VIP & Cadastro de Clientes
* **Modal de Login e Cadastro:** Acessível pelo header em **"★ Clube VIP"** ou pelo drawer mobile.
* **Benefícios:**
  * Permite aos clientes se cadastrarem com WhatsApp e criarem uma senha.
  * Habilita cupons exclusivos para clientes cadastrados.
  * Salva o histórico de compras e pedidos recorrentes no perfil do cliente.

### 3. Acompanhamento de Pedido em Tempo Real (Estilo Mercado Livre / iFood)
* **Página / Modal de Rastreio:** Acessível via botão *"Acompanhar Pedido em Tempo Real"* no pós-checkout, link no menu *"Rastrear Pedido"*, ou diretamente pela URL com parâmetro `?rastreio=DC-XXXX`.
* **Linha do Tempo Visual:**
  1. 📝 **Pedido Recebido** (Aguardando confirmação)
  2. 👨‍🍳 **Confirmado pela Cozinha** (Em fila de produção)
  3. 🔥 **No Forno / Em Preparo** (Assando)
  4. 🛵 **Saiu para Entrega** (ou 🏪 **Pronto para Retirada no Balcão**)
  5. 🍕 **Entregue / Concluído**
* **Polling Automático:** Atualiza o status na tela a cada 15 segundos sem exigir recarregar a página.

### 4. Impressão Térmica de Comanda (80mm e 58mm)
* **Rota Dedicada:** `GET /api/v1/printing/<CODIGO_DO_PEDIDO>/`
* **Layout Otimizado:** Formatação exata para bobinas térmicas de impressoras de balcão (Epson, Bematech, Daruma, Elgin):
  * Cabeçalho da Don Corleone.
  * Código do pedido em tamanho grande e negrito.
  * Modalidade em destaque (*DELIVERY 🛵* ou *RETIRADA 🏪*).
  * Endereço completo de entrega.
  * Itens detalhados com frações de sabores (½ e ⅓), adicionais de borda e observações.
  * Subtotal, desconto, taxa de entrega e Total.
  * Informações de troco para dinheiro (*LEVAR TROCO: R$ XX,XX*).
  * Parâmetro `?autoprint=1` para disparo automático de impressão.

### 5. Promoções Parametrizadas Avançadas
* **Modelagem:** Suporte a regras condicionais combinadas:
  * Desconto percentual (%) ou fixo (R$).
  * Dias específicos da semana (ex: Terça e Quarta).
  * Pedido mínimo elegível.
  * Restrição exclusiva para clientes cadastrados no Clube VIP.
  * Limite máximo de utilizações do cupom.
  * Faixa dourada no topo da landing page ligada/desligada pelo painel.

### 6. Gestão de Status pelo Painel Operacional
* **Transições Operacionais:**
  * O atendente ou a cozinha alteram o status do pedido com 1 clique:
  * `NOVO` ➔ `CONFIRMADO` ➔ `PREPARO` ➔ `SAIU_PARA_ENTREGA` / `PRONTO_RETIRADA` ➔ `CONCLUIDO` ➔ `CANCELADO`.
* **Histórico de Auditoria:** Cada mudança grava quem alterou, data, hora e observações.

### 7. Envio Automático no WhatsApp (Evolution API)
* **Disparo Automático:** Quando o pedido é marcado como `SAIU_PARA_ENTREGA`, o backend aciona a **Evolution API** enviando mensagem formatada com o link de rastreio direto no WhatsApp do cliente:
  > *"Olá, Kayron! 🛵💨 Seu pedido #DC-1310-74K da Don Corleone acabou de sair para entrega com o nosso entregador! Acompanhe em tempo real por aqui: https://doncorleonepizzas.com.br/rastreio/DC-1310-74K"*
* Quando marcado como `PRONTO_RETIRADA`, avisa que o pedido já pode ser retirado no balcão da Cidade Alta.

### 8. Telas Personalizadas e Gestão Administrativa
* **Gerenciamento do Cardápio:** Cadastrar novos sabores, mudar preços, pausar itens esgotados e alterar bordas sem encostar em código ou JSON.
* **Gestão de Bairros:** Ajustar taxas de entrega por bairro ou ativar/desativar bairros temporariamente.
* **Configurações da Loja:** Horários de atendimento, horário de corte e chave Pix.

---

## 3. Endpoints da API REST (`/api/v1/`)

| Método | Endpoint | Descrição |
|---|---|---|
| **GET** | `/api/v1/catalog/` | Retorna categorias, produtos, fotos e bordas ativas |
| **POST** | `/api/v1/catalog/toggle-availability/<uuid>/` | Ativa/desativa disponibilidade de um produto |
| **GET** | `/api/v1/delivery/config/` | Retorna bairros, taxas e horários de funcionamento |
| **POST** | `/api/v1/orders/create/` | Cria e persiste pedido no banco de dados |
| **GET** | `/api/v1/orders/admin/` | Lista pedidos com filtros por status |
| **POST** | `/api/v1/orders/admin/<uuid>/update-status/` | Atualiza status e dispara WhatsApp |
| **GET** | `/api/v1/tracking/<codigo>/` | Rastreio público com linha do tempo do pedido |
| **GET** | `/api/v1/printing/<codigo>/` | Visualização e impressão térmica da comanda |
| **POST** | `/api/v1/promotions/validate/` | Valida cupom e calcula desconto |
| **GET** | `/api/v1/promotions/banner/` | Retorna banner promocional ativo |
| **POST** | `/api/v1/accounts/register/` | Cadastro de cliente para promoções VIP |
| **POST** | `/api/v1/accounts/login/` | Autenticação de cliente |
| **GET** | `/api/v1/customers/admin/customers/` | Relatório de clientes cadastrados e VIPs |

---

## 4. Como Executar o Sistema

### 1. Iniciar o Frontend (Vite)
```bash
npm run dev
# Acesse: http://localhost:5173
```

### 2. Iniciar o Backend (Django)
```bash
# Com o terminal no diretório raiz:
.venv\Scripts\python.exe backend\manage.py migrate
.venv\Scripts\python.exe backend\manage.py import_legacy_data
.venv\Scripts\python.exe backend\manage.py createsuperuser   # login do dono (uma vez)
.venv\Scripts\python.exe backend\manage.py runserver 8000
# Painel do dono: http://localhost:8000/painel/
# Django Admin (técnico): http://localhost:8000/admin/
```

`import_legacy_data` só cria o que falta e preserva o que foi editado no painel.
Use `--sobrescrever` apenas para voltar aos valores dos arquivos `src/data/`.

### 3. Painel do dono (`/painel/`)
Telas em Django templates, acesso só para usuários da equipe (`is_staff`):
* **Início:** valor registrado, pedidos concluídos, ticket médio, cancelados (hoje / 7 / 30 dias) e avisos.
* **Pedidos:** quadro por status que se atualiza a cada 15 s com aviso sonoro; histórico com busca e filtros; detalhe com itens, endereço, troco, histórico e impressão da comanda.
* **Cardápio:** produtos, preços por tamanho, bordas, categorias e "esgotado" com 1 clique.
* **Entregas:** bairros, taxas e bairros atendidos.
* **Clientes:** todos que já pediram (pelo WhatsApp) e o Clube VIP.
* **Promoções:** cupons; a promoção com "Faixa no site" é aplicada automaticamente em todo pedido.
* **Configurações:** fechamento emergencial, horários, pedido mínimo, tempos e PIX.

O site lê esses dados do banco ao abrir (`GET /api/v1/catalog/site-data/`); se o backend
não responder em 2,5 s, usa os arquivos de `src/data/`. Para as fotos do cardápio aparecerem
no painel em produção, defina `SITE_PUBLIC_URL` com o endereço do site.
