---
name: dc-frontend-ui-ux
description: Diretrizes de design visual, UX e engenharia front-end do sistema da pizzaria (conceito "Sofisticação Rústica"): identidade visual, componentes, animações e experiência mobile.
---

# Skill de Front-End, UI e UX: Sistema de Pizzaria (Sofisticação Rústica)

Esta skill define as diretrizes de design, experiência do usuário (UX) e engenharia front-end para o desenvolvimento de um sistema digital de pizzaria. O conceito central é a **"Sofisticação Rústica"**: a fusão entre a tradição artesanal (massa fermentada lentamente, ingredientes selecionados, aconchego italiano) e a tecnologia moderna, limpa, fluida e altamente apetitosa.

---

> **Nota de marca:** a casa se apresenta como **Pizzaria & Esfiharia**. Não mencionar forno a lenha nem "Cantina" em textos, telas ou dados.

## 1. Identidade Visual e Direção de Arte (UI)

### 1.1. Paleta de Cores Sensorial
As cores devem despertar o apetite, remeter a ingredientes frescos e evocar a rusticidade elegante de uma trattoria contemporânea.

*   **Cor Primária (Terrosos & Tradicionais):**
    *   *Terracota / Tijolo Queimado* (`#C85A32`): Usada em CTAs principais e destaques de marca. Traz o calor e o aconchego da cozinha artesanal.
    *   *Marrom Mogno / Madeira Queimada* (`#2C1D18`): Para fundos escuros de alta sofisticação ou textos principais.
*   **Cor Secundária (Frescor & Naturalidade):**
    *   *Verde Manjericão Profundo* (`#1E3F20`): Elementos de sucesso, categorias naturais e selos de qualidade ("artesanal", "orgânico").
*   **Cores de Apoio (Base e Neutros):**
    *   *Farinha de Trigo / Off-White Quente* (`#F9F6F0`): Cor de fundo principal para telas claras, evitando o branco estéril e trazendo aconchego.
    *   *Creme / Queijo Mussarela Derretido* (`#F3E5AB`): Fundos de cards e elementos secundários.
*   **Cor de Destaque (Apetite):**
    *   *Vermelho Pomodoro Escuro* (`#A8201A`): Alertas de itens essenciais, promoções ou selos de desconto.

### 1.2. Tipografia com Personalidade
*   **Títulos e Destaques (Display):** Use uma fonte *Serifada de Alta Elegância* (ex: *Playfair Display*, *Lora* ou *Cormorant Garamond*). Ela transmite tradição, herança e o cuidado artesanal.
*   **Corpo de Texto e UI (Interface):** Use uma fonte *Sans-Serif geométrica e limpa* (ex: *Inter*, *Plus Jakarta Sans* ou *Outfit*). Garante legibilidade impecável em cardápios digitais e botões de checkout.

### 1.3. Texturas e Elementos Visuais
*   **Texturas Sutis:** Empregue gradientes suaves com leves granulações (*noise*) ou padrões minimalistas que lembram papel kraft reciclado ou pedra rústica, sem prejudicar a leitura.
*   **Fotografia Imersiva:** Imagens de alta qualidade com profundidade de campo (efeito *bokeh*), focando no brilho do azeite, na borda alveolada da pizza e no derretimento do queijo. Nada de fotos genéricas de banco de imagens; valorize o produto real.

---

## 2. Experiência do Usuário (UX) e Jornada de Compra

### 2.1. Princípios Norteadores
*   **Fricção Zero no Pedido:** A fome tem pressa. O fluxo do cardápio até o pagamento deve ser o mais transparente e rápido possível.
*   **Sensorialidade Digital:** O usuário precisa "sentir o cheiro e a textura" da pizza através de micro-interações, descrições ricas e imagens arrebatadoras.
*   **Customização Intuitiva:** Montar uma pizza meio a meio ou adicionar bordas recheadas deve ser visual e interativo, sem telas confusas cheias de checkboxes.

### 2.2. Jornada do Cliente (User Journey)
1.  **Chegada (Landing / Início):** Impacto visual imediato com um banner hero de tirar o fôlego e o botão claro "Fazer Pedido" ou "Ver Cardápio".
2.  **Exploração do Cardápio:** Categorias organizadas de forma lógica (Pizzas Clássicas, Especiais da casa, Entradas, Bebidas, Sobremesas). Filtros rápidos para restrições alimentares (Vegetariana, Sem Glúten).
3.  **Configuração do Produto (O "Customizador"):** 
    *   Escolha de tamanho (Broto, Média, Família).
    *   Seleção de sabores (para pizzas meio a meio, divisão visual na tela).
    *   Adicionais e bordas com feedback visual instantâneo.
4.  **Carrinho e Checkout:** Resumo claro, opção de entrega ou retirada no balcão, escolha de pagamento integrada (PIX em destaque com QR code dinâmico, cartões).
5.  **Acompanhamento (Rastreio "Do Forno à Porta"):** Linha do tempo visual rústica mostrando cada etapa: *Pedido Confirmado -> No Forno -> Embalando com Carinho -> Saiu para Entrega*.

---

## 3. Diretrizes de Front-End e Arquitetura de Componentes

### 3.1. Stack Tecnológica Sugerida
*   **Framework:** React (Next.js para SEO e performance otimizada) ou Vue.js (Nuxt).
*   **Estilização:** Tailwind CSS (utilizando variáveis CSS personalizadas para suportar o design system de tons terrosos e rústicos).
*   **Animações:** Framer Motion ou Tailwind Animations para transições fluidas e orgânicas (efeitos de fade-in ao carregar pratos, modais elegantes).

### 3.2. Componentes Chave da Interface
*   **Card de Pizza ("Menu Card"):** 
    *   Bordas arredondadas suaves (`rounded-2xl`).
    *   Sombra difusa e profunda para dar sensação de relevo (*elevation*).
    *   Badge flutuante discreta para itens "Mais Pedidos" ou "Artesanal".
*   **Botões e CTAs:** 
    *   Cantos levemente arredondados, fundo em Terracota com transição de cor suave ao passar o mouse (*hover*).
    *   Efeito de feedback tátil/clique satisfatório.
*   **Modal de Personalização:**
    *   Interface em painel deslizante (*bottom sheet* no mobile, modal centralizado no desktop) com fundos texturizados e divisões claras por etapas.

### 3.3. Performance e Acessibilidade (Web Vitals)
*   **Otimização de Imagens:** Uso estrito de formatos modernos (`WebP`, `AVIF`) com carregamento progressivo (`blur-up`) para garantir que o cardápio abra instantaneamente.
*   **Mobile-First Absoluto:** Mais de 85% dos pedidos de pizzaria ocorrem via smartphones. O layout mobile deve permitir navegação confortável com uma única mão (elementos de clique na zona natural do polegar).
*   **Acessibilidade (a11y):** Contraste rigoroso entre textos e fundos (atendendo padrões WCAG AA), tamanhos de fonte legíveis e suporte a leitores de tela para todas as etapas do pedido.

---

## 4. Diferenciais de UX para Fidelização
*   **Modo História:** Uma aba sutil contando a história da massa de fermentação natural (*sourdough*) da pizzaria, gerando conexão emocional.
*   **Salvar Favoritos:** Permitir que o cliente salve sua combinação exata de pizza com um apelido (ex: "A Favorita de Domingo") para recompra em 2 cliques.