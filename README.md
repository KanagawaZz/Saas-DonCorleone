# DonCorleone — Pizzaria & Esfiharia | Arena Cuiabá

Landing page de alta conversão e web app gastronômico para a **Don Corleone — Pizzaria & Esfiharia** (Cuiabá/MT), com personalização artesanal de pizzas (até 3 sabores), carrinho integrado, verificação de funcionamento em tempo real, pedidos enviados direto para o sistema e acompanhamento do pedido pelo site.

---

## 🛠️ Tecnologias Utilizadas

- **Vite 6+**: Bundler ultrarrápido e servidor local de desenvolvimento
- **Vanilla JavaScript (ES Modules)**: Sem frameworks pesados (sem React/Vue), carregamento instantâneo
- **Lenis**: Rolagem suave (*smooth scroll*)
- **GSAP & ScrollTrigger**: Animações de entrada e cascata nos cards gastronômicos
- **Design System com CSS Moderno**: Tokens visuais em `src/styles/tokens.css`, paleta noir/ouro envelhecido/brasa de forno (`#0C0A09`, `#B8860B`, `#E26D2B`) e tipografia clássica (*Cinzel*, *Playfair Display*, *Manrope*)

---

## 🚀 Como Executar Localmente

### 1. Pré-requisitos
- **Node.js** (versão 18+ ou LTS)
- **NPM**

### 2. Comandos
```bash
npm install
npm run dev        # Inicia o servidor local (http://localhost:3000)
npm run build      # Valida e compila os arquivos de produção para dist/
npm run preview    # Pré-visualiza o build de produção localmente
```

> **Instalar em outro computador** (backend, banco e site do zero): siga [docs/INSTALACAO-LOCAL.md](docs/INSTALACAO-LOCAL.md). **Colocar no ar:** [docs/DEPLOY.md](docs/DEPLOY.md).

### 3. Tudo de uma vez (Windows)
Dois cliques em `iniciar.cmd` (ou `.\iniciar.ps1` no terminal) sobem o WhatsApp (Docker), o sistema (Django, porta 8000) e o site (Vite, porta 3000), cada um na sua janela. O script descobre o IP do computador para o site e o painel abrirem também no celular, na mesma rede Wi-Fi. Servidores que já estiverem rodando são mantidos.

---

## 🏷️ Como Configurar e Ligar/Desligar Promoções

No arquivo [`src/data/site.config.js`](file:///c:/Users/kayron.eduardo/Documents/DonCorleone/src/data/site.config.js), localize o bloco `promocao`:

```javascript
promocao: {
  ativa: true,                          // Mude para true para ligar, ou false para desligar
  titulo: "Promoção Dia dos Namorados", // Título da campanha exibido na faixa do topo
  texto: "Ganhe 10% de desconto em todas as pizzas e esfihas!",
  inicio: "2026-06-10",                 // Data de início (formato YYYY-MM-DD)
  fim: "2026-06-12",                    // Data de término (formato YYYY-MM-DD)
  cupom: "AMOR10",                      // Código do cupom (opcional)
  descontoPercentual: 10                // % de desconto aplicado sobre os produtos no carrinho
}
```

### Regras da Promoção:
1. **Ligar uma promoção**: Defina `ativa: true`, preencha as datas no formato `YYYY-MM-DD` e informe o `descontoPercentual` (número entre 1 e 100).
2. **Desligar uma promoção**: Defina `ativa: false`. A faixa do topo desaparece imediatamente e nenhum desconto é aplicado no carrinho nem na mensagem do WhatsApp.
3. **Validade automática**: Mesmo com `ativa: true`, o sistema checa a data no fuso de Cuiabá (`America/Cuiaba`). Se a data atual estiver fora do intervalo `inicio` e `fim`, nada é exibido.

---

## 📍 Como Atualizar as Taxas de Entrega por Bairro

As taxas de entrega ficam no arquivo [`src/data/bairros.json`](file:///c:/Users/kayron.eduardo/Documents/DonCorleone/src/data/bairros.json):

```json
[
  { "cidade": "Cuiabá", "bairro": "Jardim Cuiabá", "taxa": 8.00 },
  { "cidade": "Cuiabá", "bairro": "Goiabeiras", "taxa": 8.00 },
  { "cidade": "Várzea Grande", "bairro": "Centro (VG)", "taxa": 14.00 }
]
```

- Para alterar o valor de um bairro: basta trocar o número em `taxa` (em reais).
- Para adicionar um novo bairro: inclua um novo objeto com `cidade`, `bairro` e `taxa`.
- O cliente também conta com a opção *"Outro bairro (a confirmar)"*, que envia a taxa como pendente de confirmação com a atendente.
- Na **Retirada no Balcão**, a taxa é automaticamente R$ 0,00 (Grátis).

---

## ⏰ Horário de Funcionamento e Horário de Corte

No arquivo [`src/data/site.config.js`](file:///c:/Users/kayron.eduardo/Documents/DonCorleone/src/data/site.config.js):

- `horario.horaAbertura`: Hora de início dos atendimentos (padrão: `17` = 17:00).
- `horario.horaFechamento`: Hora limite de funcionamento da casa (padrão: `23` = 23:00).
- `horario.horarioCorte`: Último horário para aceitar novos pedidos na cozinha (padrão: `"22:30"`). Das 22:30 em diante, o botão de finalização no checkout é automaticamente bloqueado com aviso *"Pedidos encerrados por hoje"*.

---

## 💳 Chave Pix e Pagamentos

No arquivo [`src/data/site.config.js`](file:///c:/Users/kayron.eduardo/Documents/DonCorleone/src/data/site.config.js) no bloco `pagamento`:

- `pix.chave`: Chave Pix exibida na tela pós-envio com botão de cópia de 1 clique.
- `pix.tipo`: Tipo da chave (ex: `"Celular / WhatsApp"`, `"CNPJ"`, `"Chave Aleatória"`).
- `pix.titular`: Nome da empresa/titular da conta.
- `tempoMedioEspera`: Tempo médio estimado exibido para pedidos em dinheiro ou cartão (ex: `"40 min"`).

---

## 📲 WhatsApp automático (Evolution API)

O WhatsApp não recebe pedidos: ele só avisa o cliente quando o pedido **sai para entrega** ou fica **pronto para retirada**. Quem envia é a [Evolution API](https://doc.evolution-api.com), rodando no Docker.

1. Copie `.env.example` para `.env` na raiz e troque `EVOLUTION_API_KEY` e `EVOLUTION_DB_PASSWORD` por valores longos e aleatórios.
2. Suba os containers (Evolution + Postgres próprio, na porta `8081`, acessível só pela própria máquina):
   ```bash
   docker compose up -d
   ```
3. Reinicie o backend Django (ele lê o mesmo `.env`).
4. No painel, abra **WhatsApp**, confirme o nome da instância e clique em **Criar e gerar QR Code**. Escaneie com o WhatsApp da pizzaria em *Aparelhos conectados*. A tela atualiza sozinha quando conecta.
5. Use **Enviar teste** para conferir. Se a conexão cair, volte na mesma tela e gere um novo QR Code.

A conexão fica salva no volume do Docker: `docker compose down` não desconecta o WhatsApp (`docker compose down -v` apaga tudo).

---

## 📦 Estrutura de Arquivos

```text
DonCorleone/
├── index.html                   # HTML base, metadados OpenGraph e Schema.org
├── package.json                 # Dependências (Vite, GSAP, Lenis, Three.js)
├── vite.config.js               # Configuração do Vite
├── src/
│   ├── main.js                  # Ponto de entrada da aplicação
│   ├── data/
│   │   ├── site.config.js       # Central de configurações, Pix, horários e promoções
│   │   ├── cardapio.json        # Catálogo de pizzas, esfihas e sobremesas
│   │   ├── bairros.json         # Tabela de bairros e taxas de entrega (Cuiabá e VG)
│   │   └── depoimentos.json     # Avaliações da cantina
│   ├── utils/
│   │   ├── entrega.js           # Cálculo puro de taxa de entrega por modalidade/bairro
│   │   ├── pedidos-recentes.js  # Pedidos feitos no aparelho (atalho para o acompanhamento)
│   │   ├── horario.js           # Verificação de funcionamento e corte (fuso Cuiabá)
│   │   ├── promocao.js          # Validação e cálculo de campanhas ativas
│   │   ├── carrinho.js          # Store reativa do carrinho com sessionStorage
│   │   └── calculo-pizza.js     # Regras de fatias e maior valor
│   ├── components/
│   │   ├── header.js            # Topo com barra de progresso dourada e carrinho
│   │   ├── banner-promocao.js   # Faixa de destaque para campanhas ativas
│   │   ├── carrinho-modal.js    # Checkout em 5 passos, autopreenchimento e tela pós-envio
│   │   ├── barra-pedido.js      # Barra flutuante inferior para mobile
│   │   └── ...
│   └── styles/
│       ├── tokens.css           # Design tokens e variáveis de cores/sombras
│       ├── base.css             # Estilos globais e componentes base
│       └── components/          # Estilos individuais dos componentes
```
