import { formatarPreco, esc } from '../utils/dom.js';
import { carrinho } from '../utils/carrinho.js';
import { gsap, ScrollTrigger } from '../utils/motion.js';
import { icone } from '../utils/icons.js';
import { obterStatusFuncionamento } from '../utils/horario.js';
import { exibirModalAvisoHorarioPizza } from './modal-aviso-horario.js';
import dadosCardapioPadrao from '../data/cardapio.json';

/**
 * Renderiza a régua sofisticada de preços por tamanho (P · M · G) para pizzas.
 */
function renderTamanhosPizzaBar(item) {
  const isPremium = item.categoriaPreco === 'premium' || item.preco === 86.9;
  const precos = isPremium
    ? { p: '61,90', m: '72,90', g: '86,90' }
    : { p: '45,90', m: '62,90', g: '76,90' };

  return `
    <div class="cardapio-tamanhos-bar" aria-label="Preços por tamanho: Pequena, Média e Grande">
      <div class="tamanhos-bar-item" title="Pequena: 25 cm · 4 fatias (até 2 sabores)">
        <span class="tamanhos-bar-sigla">P</span>
        <span class="tamanhos-bar-preco"><span class="tamanhos-bar-cifrao">R$</span>${precos.p}</span>
      </div>
      <div class="tamanhos-bar-item" title="Média: 30 cm · 6 fatias (até 2 sabores)">
        <span class="tamanhos-bar-sigla">M</span>
        <span class="tamanhos-bar-preco"><span class="tamanhos-bar-cifrao">R$</span>${precos.m}</span>
      </div>
      <div class="tamanhos-bar-item" title="Grande: 35 cm · 8 fatias (até 3 sabores)">
        <span class="tamanhos-bar-sigla">G</span>
        <span class="tamanhos-bar-preco"><span class="tamanhos-bar-cifrao">R$</span>${precos.g}</span>
      </div>
    </div>
  `;
}

/**
 * Renderiza o card individual de um produto com formatação de preço e botões de ação.
 */
export function renderizarCardItem(item, catId = '') {
  const effectiveCatId = item.categoriaId || catId;
  const isPizzaCategory = effectiveCatId === 'pizzas-salgadas' || effectiveCatId === 'pizzas-doces' || item.tipo === 'pizza';

  let precoExibido = '';
  if (isPizzaCategory) {
    const isPrem = item.categoriaPreco === 'premium' || item.preco === 86.9;
    precoExibido = isPrem ? 'A partir de R$ 61,90' : 'A partir de R$ 45,90';
  } else if (typeof item.preco === 'number' && item.preco > 0) {
    precoExibido = formatarPreco(item.preco);
  } else if (item.preco === 0) {
    precoExibido = 'Sem adicional';
  } else {
    precoExibido = item.precoTexto || 'Sob consulta';
  }

  const itemJson = JSON.stringify({ ...item, categoriaId: effectiveCatId }).replace(/"/g, '&quot;');

  // Nome formatado para deixar explícito quando é pizza (evita qualquer ambiguidade com esfihas)
  const nomeExibido = isPizzaCategory && !item.nome.toLowerCase().startsWith('pizza')
    ? (effectiveCatId === 'pizzas-doces' ? `Pizza Doce ${item.nome}` : `Pizza ${item.nome}`)
    : item.nome;

  const categoriaLabels = {
    'pizzas-salgadas': '🍕 Pizza Salgada',
    'pizzas-doces': '🍕 Pizza Doce',
    'combos-pizzas': '🎁 Combo',
    'esfihas-unitarias': '🥟 Esfiha',
    'kits-esfihas': '📦 Kit Esfihas',
    'bebidas': '🥤 Bebida'
  };
  const categoriaBadgeText = categoriaLabels[effectiveCatId] || item.categoriaNome || '';

  return `
  <article class="cardapio-item-card" data-reveal>
    <div class="cardapio-card-frame" aria-hidden="true"></div>

    <div class="cardapio-item-img-wrap">
      <img src="${item.foto || '/images/cardapio/calabresa-artesanal.webp'}" alt="${esc(nomeExibido)}" loading="lazy" class="cardapio-item-img" />
      
      <div class="cardapio-item-badges-bar">
        ${item.tag ? `
          <span class="cardapio-item-tag">
            <span class="tag-fire-icon">✦</span>
            <span>${esc(item.tag)}</span>
          </span>
        ` : `
          <span class="cardapio-item-tag-subtle">
            <span>${esc(categoriaBadgeText)}</span>
          </span>
        `}

        ${categoriaBadgeText && item.tag ? `
          <span class="cardapio-item-cat-pill">
            <span>${esc(categoriaBadgeText)}</span>
          </span>
        ` : ''}
      </div>
      
      <div class="cardapio-img-overlay"></div>
      <div class="cardapio-ember-glow" aria-hidden="true"></div>
    </div>
    
    <div class="cardapio-item-info">
      <div class="cardapio-item-header">
        <h3 class="cardapio-item-nome">${esc(nomeExibido)}</h3>
        <div class="cardapio-item-preco-box">
          <span class="cardapio-item-preco ${!item.preco ? 'preco-consulta' : ''}">${precoExibido}</span>
          ${isPizzaCategory ? renderTamanhosPizzaBar(item) : ''}
        </div>
      </div>
      
      <div class="cardapio-ornament-line" aria-hidden="true"></div>

      ${item.descricao ? `
        <p class="cardapio-item-desc">${esc(item.descricao)}</p>
      ` : ''}
      
      ${item.composicao ? `
        <div class="cardapio-badge-composicao">
          <strong>Composição:</strong> ${esc(item.composicao)}
        </div>
      ` : ''}

      ${item.distribuicao ? `
        <div class="cardapio-badge-composicao">
          <strong>Distribuição:</strong> ${esc(item.distribuicao)}
        </div>
      ` : ''}

      <div class="cardapio-item-footer">
        ${isPizzaCategory ? `
          <button type="button" class="btn btn--primary btn--customizar-pizza" data-item-data="${itemJson}">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
            <span>Montar Pizza</span>
          </button>
        ` : `
          <button type="button" class="btn btn--primary btn--pedir-simples" data-item-data="${itemJson}">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <circle cx="9" cy="21" r="1"></circle>
              <circle cx="20" cy="21" r="1"></circle>
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
            </svg>
            <span>${item.preco ? 'Adicionar ao Carrinho' : 'Adicionar ao Pedido'}</span>
          </button>
        `}
      </div>
    </div>
  </article>
  `;
}

export function renderCardapio(config, dadosCardapio = dadosCardapioPadrao) {
  const cardapioTextos = config.textos?.cardapio || {};
  const categorias = dadosCardapio?.categorias || [];
  const pedidoMinimo = config.regrasComerciais?.pedidoMinimo || config.pagamento?.pedidoMinimo || 23.00;

  // Extrair itens em destaque (combos e mais pedidos)
  const itensDestaque = [];
  categorias.forEach(cat => {
    (cat.itens || []).forEach(item => {
      if (item.destaque) {
        itensDestaque.push({ ...item, categoriaId: cat.id, categoriaNome: cat.nome });
      }
    });
  });

  // Ícones por categoria para navegação rápida e visual
  const iconesCategorias = {
    'pizzas-salgadas': 'pizza',
    'pizzas-doces': 'doce',
    'combos-pizzas': 'presente',
    'esfihas-unitarias': 'esfiha',
    'kits-esfihas': 'caixa',
    'bebidas': 'bebida'
  };

  // 1. CARDS DE DESTAQUES (PRIMEIRO NO CARDÁPIO - INSPIRADO NO LAYOUT MOBILE APP)
  const destaquesHtml = itensDestaque.slice(0, 6).map(item => {
    const isPizza = item.categoriaId === 'pizzas-salgadas' || item.categoriaId === 'pizzas-doces';
    let precoTxt = '';
    if (isPizza) {
      precoTxt = (item.categoriaPreco === 'premium' || item.preco === 86.9)
        ? 'A partir de R$ 61,90'
        : 'A partir de R$ 45,90';
    } else if (typeof item.preco === 'number' && item.preco > 0) {
      precoTxt = formatarPreco(item.preco);
    } else {
      precoTxt = item.precoTexto || 'Sob consulta';
    }
    const itemJson = JSON.stringify(item).replace(/"/g, '&quot;');

    return `
    <div class="destaque-card-mini" data-reveal>
      <div class="destaque-card-img-wrap">
        <img src="${item.foto || '/images/cardapio/calabresa-artesanal.webp'}" alt="${esc(item.nome)}" loading="lazy" class="destaque-card-img" />
        <span class="destaque-pill-tag">${esc(item.tag || 'Destaque')}</span>
      </div>
      <div class="destaque-card-info">
        <h4 class="destaque-card-title">${esc(item.nome)}</h4>
        <p class="destaque-card-desc">${esc(item.descricao || '')}</p>
        <div class="destaque-card-bottom">
          <span class="destaque-card-price ${!item.preco ? 'preco-consulta-mini' : ''}">${precoTxt}</span>
          ${isPizza ? `
            <button type="button" class="btn-mini-action btn--customizar-pizza" data-item-data="${itemJson}" title="Montar Pizza">
              <span>Montar</span>
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>
          ` : `
            <button type="button" class="btn-mini-action btn--pedir-simples" data-item-data="${itemJson}" title="Adicionar">
              <span>Pedir</span>
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            </button>
          `}
        </div>
      </div>
    </div>
    `;
  }).join('');

  // 2. ABAS DE CATEGORIAS (NAVEGAÇÃO RÁPIDA E INTUITIVA)
  const abasHtml = categorias.map((cat, idx) => {
    const iconeSvg = icone(iconesCategorias[cat.id] || 'estrela', 16);
    const totalItens = (cat.itens || []).length;
    return `
    <button type="button" role="tab" class="tab-btn ${idx === 0 ? 'active' : ''}" id="tab-${idx}" aria-selected="${idx === 0}" aria-controls="panel-${idx}">
      <span class="tab-btn-icon">${iconeSvg}</span>
      <span class="tab-btn-label">${esc(cat.nome)}</span>
      <span class="tab-btn-count">${totalItens}</span>
    </button>
    `;
  }).join('');

  // 3. PAINÉIS DE CATEGORIAS
  const paineisHtml = categorias.map((cat, idx) => {
    const itensGrid = (cat.itens || []).map(item => renderizarCardItem(item, cat.id)).join('');

    return `
    <div role="tabpanel" class="tab-panel ${idx === 0 ? 'active' : ''}" id="panel-${idx}" aria-labelledby="tab-${idx}">
      ${cat.descricao ? `<p class="cat-descricao text-center mb-6">${esc(cat.descricao)}</p>` : ''}
      <div class="cardapio-grid">
        ${itensGrid}
      </div>
    </div>
    `;
  }).join('');

  return `
  <section id="cardapio" class="secao-cardapio" aria-labelledby="cardapio-titulo">
    <div class="container">
      
      <!-- Cabeçalho da Seção -->
      <div class="text-center section-header-wrap">
        <span class="section-tag">${cardapioTextos.tituloItaliano || 'La Nostra Carta'}</span>
        <h2 id="cardapio-titulo" class="section-title">${cardapioTextos.titulo || 'Nosso Cardápio'}</h2>
        <p class="section-subtitle mb-6">
          ${cardapioTextos.subtitulo || 'Pizzas artesanais, esfihas recheadas, combos e kits especiais em Cuiabá.'}
        </p>
        
        <!-- Guia Oficial de Tamanhos e Regras Comerciais -->
        <div class="cardapio-info-banner">
          <div class="info-banner-item">
            <span class="info-banner-icon">${icone('pizza', 22)}</span>
            <div class="info-banner-text">
              <strong>Tamanhos &amp; Preços Oficiais:</strong>
              <span>Tradicionais (P 45,90 · M 62,90 · G 76,90) · Premium (P 61,90 · M 72,90 · G 86,90) · Borda Catupiry Grátis!</span>
            </div>
          </div>
          <div class="info-banner-divider" aria-hidden="true"></div>
          <div class="info-banner-item">
            <span class="info-banner-icon">${icone('entrega', 22)}</span>
            <div class="info-banner-text">
              <strong>Pedido Mínimo:</strong>
              <span>${formatarPreco(pedidoMinimo)} para entregas e atendimento</span>
            </div>
          </div>
        </div>
      </div>

      <!-- SEÇÃO DE DESTAQUES & COMBOS (MOSTRAR PRIMEIRO OS DESTAQUES) -->
      <div class="cardapio-destaques-secao mt-10 mb-12">
        <div class="destaques-header">
          <div class="destaques-title-wrap">
            <span class="destaques-badge-fire">${icone('fogo', 13)} Os Favoritos da Casa</span>
            <h3 class="destaques-section-title">Destaques &amp; Mais Pedidos</h3>
            <p class="destaques-section-sub">Combos e sabores imperdíveis preparados para compartilhar.</p>
          </div>
        </div>

        <div class="destaques-horizontal-grid">
          ${destaquesHtml}
        </div>
      </div>

      <!-- BARRA DE BUSCA EM TEMPO REAL POR PRODUTO E SABOR -->
      <div class="cardapio-busca-wrapper" id="cardapio-busca-wrapper">
        <div class="cardapio-busca-inner">
          <div class="cardapio-busca-input-box">
            <svg class="busca-icon-lupa" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input 
              type="text" 
              id="input-busca-cardapio" 
              class="cardapio-busca-input" 
              placeholder="Buscar pizza, esfiha ou sabor..." 
              autocomplete="off"
              aria-label="Pesquisar no cardápio"
            />
            <button type="button" class="btn-limpar-busca" id="btn-limpar-busca-cardapio" style="display: none;" title="Limpar busca" aria-label="Limpar pesquisa">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          <!-- Atalhos Rápidos (Chips) -->
          <div class="cardapio-busca-chips">
            <span class="chips-label">Sugestões:</span>
            <button type="button" class="busca-chip" data-termo="Calabresa">Calabresa</button>
            <button type="button" class="busca-chip" data-termo="Frango">Frango</button>
            <button type="button" class="busca-chip" data-termo="Queijo">Queijo</button>
            <button type="button" class="busca-chip" data-termo="Esfiha">Esfihas</button>
            <button type="button" class="busca-chip" data-termo="Combo">Combos</button>
            <button type="button" class="busca-chip" data-termo="Chocolate">Doces</button>
            <button type="button" class="busca-chip" data-termo="Bebida">Bebidas</button>
          </div>
        </div>

        <!-- Indicador de Status da Busca (exibido quando usuário digita) -->
        <div class="cardapio-busca-status" id="cardapio-busca-status" style="display: none;">
          <span id="cardapio-busca-contador"></span>
          <button type="button" class="btn-voltar-categorias" id="btn-voltar-categorias">Ver todas as categorias</button>
        </div>
      </div>

      <!-- PAINEL EXCLUSIVO DE RESULTADOS DA BUSCA -->
      <div class="cardapio-busca-resultados" id="cardapio-busca-resultados" style="display: none;">
        <div class="cardapio-grid" id="cardapio-busca-grid"></div>
      </div>

      <!-- NAVEGAÇÃO RÁPIDA POR CATEGORIAS (STICKY NO SCROLL) -->
      <div class="cardapio-tabs-wrapper-sticky" id="cardapio-nav-sticky">
        <div class="cardapio-tabs-scroll-container">
          <div class="cardapio-tabs" role="tablist" aria-label="Categorias do cardápio">
            ${abasHtml}
          </div>
        </div>
      </div>

      <!-- PAINÉIS DO CARDÁPIO COMPLETO -->
      <div class="cardapio-paineis mt-8" id="cardapio-paineis-container">
        ${paineisHtml}
      </div>

      <!-- Banner de Fechamento do Cardápio -->
      <div class="cardapio-footer-banner text-center mt-12">
        <div class="banner-inner">
          <p class="banner-text">Pronto para revisar seus itens e enviar o pedido?</p>
          <button type="button" class="btn btn--outline btn--gold btn--abrir-checkout">
            <span>Ver Meu Pedido no Carrinho</span>
          </button>
        </div>
      </div>

    </div>
  </section>
  `;
}

export function initCardapio(config, dadosCardapio = dadosCardapioPadrao) {
  const tabs = document.querySelectorAll('.cardapio-tabs .tab-btn');
  const panels = document.querySelectorAll('.cardapio-paineis .tab-panel');
  const inputBusca = document.querySelector('#input-busca-cardapio');
  const btnLimparBusca = document.querySelector('#btn-limpar-busca-cardapio');
  const chips = document.querySelectorAll('.busca-chip');
  const buscaStatus = document.querySelector('#cardapio-busca-status');
  const buscaContador = document.querySelector('#cardapio-busca-contador');
  const btnVoltarCategorias = document.querySelector('#btn-voltar-categorias');
  const painelResultados = document.querySelector('#cardapio-busca-resultados');
  const gridResultados = document.querySelector('#cardapio-busca-grid');
  const navTabsSticky = document.querySelector('#cardapio-nav-sticky');
  const paineisContainer = document.querySelector('#cardapio-paineis-container');

  // Coleta todos os itens do cardápio em um array único para busca instantânea
  const todosItens = [];
  (dadosCardapio?.categorias || []).forEach(cat => {
    (cat.itens || []).forEach(item => {
      todosItens.push({
        ...item,
        categoriaId: cat.id,
        categoriaNome: cat.nome
      });
    });
  });

  const normalizar = (str) => {
    return (str || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  };

  const animarCascataCards = (painel) => {
    if (!painel) return;
    const cards = painel.querySelectorAll('.cardapio-item-card');
    if (!cards || cards.length === 0) return;

    gsap.fromTo(cards, 
      { opacity: 0, y: 24, scale: 0.98 },
      { 
        opacity: 1, 
        y: 0, 
        scale: 1, 
        duration: 0.4, 
        stagger: 0.05, 
        ease: "power2.out",
        overwrite: "auto"
      }
    );
  };

  if (typeof ScrollTrigger !== 'undefined') {
    ScrollTrigger.create({
      trigger: '#cardapio',
      start: 'top 75%',
      once: true,
      onEnter: () => {
        const painelAtivo = document.querySelector('.cardapio-paineis .tab-panel.active');
        animarCascataCards(painelAtivo);
      }
    });
  }

  // Navegação por abas
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      panels.forEach(p => {
        p.classList.remove('active');
      });

      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');

      // Scroll horizontal da aba ativa para ficar no campo visual no mobile
      tab.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });

      if (panels[index]) {
        panels[index].classList.add('active');
        animarCascataCards(panels[index]);
      }
    });
  });

  // ==========================================================================
  // LÓGICA DA BARRA DE BUSCA EM TEMPO REAL
  // ==========================================================================
  const executarBusca = (termo) => {
    const termoLimpo = termo.trim();
    const termoNorm = normalizar(termoLimpo);

    if (!termoNorm) {
      limparBusca();
      return;
    }

    if (btnLimparBusca) btnLimparBusca.style.display = 'flex';

    const palavras = termoNorm.split(/\s+/).filter(Boolean);

    // Avalia e pontua cada item para priorizar:
    // 1º: Match no Título / Nome da pizza (exato > começa com > contém termo completo > contém palavras)
    // 2º: Match nos Ingredientes / Descrição / Composição
    // 3º: Match em Tags / Categorias
    const resultados = [];

    todosItens.forEach(item => {
      const isPizza = item.categoriaId === 'pizzas-salgadas' || item.categoriaId === 'pizzas-doces';
      const nomeExibido = isPizza && !item.nome.toLowerCase().startsWith('pizza') 
        ? (item.categoriaId === 'pizzas-doces' ? `Pizza Doce ${item.nome}` : `Pizza ${item.nome}`)
        : item.nome;

      const nomeNorm = normalizar(nomeExibido);
      // Extrai sabor principal removendo prefixos genéricos (ex: "esfiha de carne" -> "carne")
      const saborNorm = nomeNorm
        .replace(/^(pizza doce de|pizza doce|pizza de|pizza|esfiha doce de|esfiha doce|esfiha de|esfiha|kit esfiha|kit|combo)\s+/g, '')
        .trim();

      const descNorm = normalizar(item.descricao);
      const compNorm = normalizar(item.composicao);
      const distNorm = normalizar(item.distribuicao);
      const tagNorm = normalizar(item.tag);
      const catNorm = normalizar(item.categoriaNome);

      const ingredientesNorm = `${descNorm} ${compNorm} ${distNorm}`.trim();

      let score = 0;
      let matchTipo = null; // 'titulo' | 'ingrediente' | 'outro'

      // --- 1. AVALIAÇÃO DE PRIORIDADE NO TÍTULO / SABOR ---
      // 1.1 Match exato no sabor principal (ex: busca "carne" -> "Esfiha de Carne" pontua 1200!)
      if (saborNorm === termoNorm || nomeNorm === termoNorm) {
        score = 1200;
        matchTipo = 'titulo';
      } 
      // 1.2 Variações diretas do sabor (ex: "carne com queijo", "carne com catupiry")
      else if (saborNorm.startsWith(termoNorm + ' com ') || saborNorm.startsWith(termoNorm + ' e ') || saborNorm.startsWith(termoNorm + ' c/')) {
        score = 900;
        matchTipo = 'titulo';
      }
      // 1.3 Sabores compostos derivados (ex: "carne seca")
      else if (saborNorm.startsWith(termoNorm) || nomeNorm.startsWith(termoNorm)) {
        score = 750;
        matchTipo = 'titulo';
      } 
      // 1.4 Contém o termo completo no nome
      else if (saborNorm.includes(termoNorm) || nomeNorm.includes(termoNorm)) {
        score = 600;
        matchTipo = 'titulo';
      } else if (palavras.length > 1 && palavras.every(p => nomeNorm.includes(p))) {
        score = 500;
        matchTipo = 'titulo';
      } else if (palavras.some(p => nomeNorm.includes(p))) {
        const palavrasNoNome = palavras.filter(p => nomeNorm.includes(p)).length;
        score = 300 + (palavrasNoNome / palavras.length) * 100;
        matchTipo = 'titulo';
      }

      // --- 2. AVALIAÇÃO DE PRIORIDADE NOS INGREDIENTES / DESCRIÇÃO ---
      if (!matchTipo) {
        if (ingredientesNorm.includes(termoNorm)) {
          score = 200;
          matchTipo = 'ingrediente';
        } else if (palavras.length > 1 && palavras.every(p => ingredientesNorm.includes(p))) {
          score = 150;
          matchTipo = 'ingrediente';
        } else if (palavras.some(p => ingredientesNorm.includes(p))) {
          const palavrasNosIngr = palavras.filter(p => ingredientesNorm.includes(p)).length;
          score = 100 + (palavrasNosIngr / palavras.length) * 40;
          matchTipo = 'ingrediente';
        }
      } else {
        // Bônus se também tem nos ingredientes
        if (ingredientesNorm.includes(termoNorm)) {
          score += 20;
        }
      }

      // --- 3. AVALIAÇÃO EM TAGS OU CATEGORIAS (se ainda não encontrou) ---
      if (!matchTipo) {
        if (tagNorm.includes(termoNorm) || catNorm.includes(termoNorm) || palavras.some(p => tagNorm.includes(p) || catNorm.includes(p))) {
          score = 50;
          matchTipo = 'outro';
        }
      }

      if (score > 0) {
        if (item.destaque) score += 2;

        resultados.push({
          ...item,
          score,
          matchTipo
        });
      }
    });

    // Ordenação estrita por pontuação decrescente:
    // Garante que Sabor Exato vem PRIMEIRO, seguido por variações, derivados e ingredientes.
    resultados.sort((a, b) => b.score - a.score);

    const encontrados = resultados;

    // Oculta visualização padrão por abas
    if (navTabsSticky) navTabsSticky.style.display = 'none';
    if (paineisContainer) paineisContainer.style.display = 'none';

    // Exibe painel de resultados e status
    if (buscaStatus) buscaStatus.style.display = 'flex';
    if (painelResultados) painelResultados.style.display = 'block';

    if (encontrados.length > 0) {
      if (buscaContador) {
        const porTitulo = encontrados.filter(i => i.matchTipo === 'titulo').length;
        const porIngredientes = encontrados.filter(i => i.matchTipo === 'ingrediente').length;

        if (porTitulo > 0 && porIngredientes > 0) {
          buscaContador.innerHTML = `Encontramos <strong>${encontrados.length}</strong> produto(s) para "${esc(termoLimpo)}" <span class="busca-detalhe-pill">${porTitulo} no título · ${porIngredientes} nos ingredientes</span>`;
        } else {
          buscaContador.innerHTML = `Encontramos <strong>${encontrados.length}</strong> produto(s) para "${esc(termoLimpo)}"`;
        }
      }
      if (gridResultados) {
        gridResultados.innerHTML = encontrados.map(item => renderizarCardItem(item, item.categoriaId)).join('');
        animarCascataCards(gridResultados);
      }
    } else {
      if (buscaContador) {
        buscaContador.innerHTML = `Nenhum resultado para "${esc(termoLimpo)}"`;
      }
      if (gridResultados) {
        gridResultados.innerHTML = `
          <div class="busca-vazia-box">
            <svg viewBox="0 0 24 24" width="44" height="44" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <h4>Nenhum produto encontrado para "${esc(termoLimpo)}"</h4>
            <p>Tente buscar por outro sabor ou ingrediente, como Calabresa, Catupiry, Carne, Chocolate ou Coca-Cola.</p>
            <button type="button" class="btn btn--outline btn--gold" id="btn-limpar-busca-vazio">
              <span>Ver Todo o Cardápio</span>
            </button>
          </div>
        `;

        document.querySelector('#btn-limpar-busca-vazio')?.addEventListener('click', limparBusca);
      }
    }
  };

  const limparBusca = () => {
    if (inputBusca) inputBusca.value = '';
    if (btnLimparBusca) btnLimparBusca.style.display = 'none';
    if (buscaStatus) buscaStatus.style.display = 'none';
    if (painelResultados) painelResultados.style.display = 'none';
    if (gridResultados) gridResultados.innerHTML = '';
    
    // Restaura visualização por abas
    if (navTabsSticky) navTabsSticky.style.display = 'block';
    if (paineisContainer) paineisContainer.style.display = 'block';

    // Desmarca chips ativos
    chips.forEach(c => c.classList.remove('active'));

    const painelAtivo = document.querySelector('.cardapio-paineis .tab-panel.active');
    if (painelAtivo) animarCascataCards(painelAtivo);
  };

  // Digitação em tempo real
  inputBusca?.addEventListener('input', (e) => {
    const digitado = e.target.value;
    chips.forEach(c => c.classList.remove('active'));
    executarBusca(digitado);
  });

  // Botões de limpar busca
  btnLimparBusca?.addEventListener('click', () => {
    limparBusca();
    inputBusca?.focus();
  });

  btnVoltarCategorias?.addEventListener('click', () => {
    limparBusca();
  });

  // Chips de atalho rápido
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const termo = chip.dataset.termo || '';
      const jaAtivo = chip.classList.contains('active');

      chips.forEach(c => c.classList.remove('active'));

      if (jaAtivo) {
        limparBusca();
      } else {
        chip.classList.add('active');
        if (inputBusca) inputBusca.value = termo;
        executarBusca(termo);
      }
    });
  });

  // ==========================================================================
  // DELEGAÇÃO DE EVENTOS DE AÇÃO DO CARDÁPIO (BOTÕES DE MONTAGEM E ADIÇÃO)
  // ==========================================================================
  const secaoCardapio = document.querySelector('#cardapio');
  secaoCardapio?.addEventListener('click', (e) => {
    // 1. Botão de Montar Pizza
    const btnCustomizar = e.target.closest('.btn--customizar-pizza');
    if (btnCustomizar) {
      e.preventDefault();
      let itemData = null;
      try {
        itemData = JSON.parse(btnCustomizar.dataset.itemData);
      } catch (err) {}

      const status = obterStatusFuncionamento(new Date(), config.horario || {});
      if (!status.podeFazerPedido) {
        exibirModalAvisoHorarioPizza({
          itemData,
          status,
          onSimular: (dados) => {
            carrinho.abrirModalPizza(dados);
          }
        });
        return;
      }

      carrinho.abrirModalPizza(itemData);
      return;
    }

    // 2. Botão de Escolher Borda (abre montador de pizza)
    const btnBorda = e.target.closest('.btn--abrir-montador-borda');
    if (btnBorda) {
      e.preventDefault();
      const status = obterStatusFuncionamento(new Date(), config.horario || {});
      if (!status.podeFazerPedido) {
        exibirModalAvisoHorarioPizza({
          itemData: null,
          status,
          onSimular: () => {
            carrinho.abrirModalPizza();
          }
        });
        return;
      }

      carrinho.abrirModalPizza();
      return;
    }

    // 3. Botão de Pedir Item Simples (Esfihas, Combos, Bebidas)
    const btnSimples = e.target.closest('.btn--pedir-simples');
    if (btnSimples) {
      e.preventDefault();
      try {
        const itemData = JSON.parse(btnSimples.dataset.itemData);
        carrinho.adicionarItemSimples(itemData, 1);
        carrinho.abrirModalCheckout();
      } catch (err) {
        console.error('Erro ao adicionar item simples:', err);
      }
      return;
    }

    // 4. Botão de Abrir Checkout
    const btnCheckout = e.target.closest('.btn--abrir-checkout');
    if (btnCheckout) {
      e.preventDefault();
      carrinho.abrirModalCheckout();
      return;
    }
  });
}
