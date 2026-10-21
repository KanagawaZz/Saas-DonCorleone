import { rolarPara } from '../utils/motion.js';
import { carrinho } from '../utils/carrinho.js';
import { icone } from '../utils/icons.js';

export function renderHeader(config) {
  const marca = config.marca || {};
  const logoUrl = (marca.usarLogoOriginal && marca.logoOriginalUrl) ? marca.logoOriginalUrl : marca.brasaoUrl;
  const qtdItens = carrinho.obterQuantidadeTotal();

  return `
  <header class="site-header" id="site-header">
    <!-- Linha Dourada de Progresso do Scroll (2px) -->
    <div class="header-scroll-progress" id="header-scroll-progress" aria-hidden="true"></div>

    <div class="container header-container">
      
      <!-- Logotipo & Nome da Marca -->
      <a href="#" class="header-brand" aria-label="Don Corleone - Início">
        <img src="${logoUrl}" alt="Don Corleone Brasão" class="header-logo-img" width="44" height="44" />
        <div class="header-brand-text">
          <span class="header-brand-name">${marca.nome || 'Don Corleone'}</span>
          <span class="header-brand-desc">${marca.slogan || 'Sabor incomparável'}</span>
        </div>
      </a>

      <!-- Navegação Principal Desktop -->
      <nav class="header-nav" aria-label="Navegação principal">
        <ul class="nav-list">
          <li><a href="#montagem" class="nav-link">Início</a></li>
          <li><a href="#cardapio" class="nav-link">Cardápio</a></li>
          <li><a href="#como-pedir" class="nav-link">Como Pedir</a></li>
          <li><a href="#sobre" class="nav-link">Sobre</a></li>
          <li><a href="#rastreio" class="nav-link" id="nav-link-rastreio">Rastrear Pedido</a></li>
          <li><a href="#clube" class="nav-link" id="nav-link-clube" style="color: #C8A15A; font-weight: bold;">★ Clube VIP</a></li>
          <li><a href="#contato" class="nav-link">Contato</a></li>
        </ul>
      </nav>

      <!-- Ações do Header -->
      <div class="header-actions">
        <!-- Botão Carrinho com Contador -->
        <button type="button" class="btn-header-cart" id="btn-header-cart" aria-label="Ver carrinho de pedidos">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="8" cy="21" r="1"></circle>
            <circle cx="19" cy="21" r="1"></circle>
            <path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"></path>
          </svg>
          <span class="cart-count-badge ${qtdItens > 0 ? 'visible' : ''}" id="cart-count-badge">${qtdItens}</span>
        </button>

        <button type="button" class="btn btn--primary btn--header-order" id="btn-header-order">
          ${icone('pizza', 18, 'btn-icon')}
          <span class="btn-text-desktop">Fazer Pedido</span>
          <span class="btn-text-mobile">Pedir</span>
        </button>

        <!-- Botão Menu Mobile -->
        <button type="button" class="mobile-menu-toggle" id="mobile-menu-toggle" aria-expanded="false" aria-label="Abrir menu de navegação">
          <span class="hamburger-line"></span>
          <span class="hamburger-line"></span>
          <span class="hamburger-line"></span>
        </button>
      </div>

    </div>

    <!-- Gaveta de Navegação Mobile -->
    <div class="mobile-drawer" id="mobile-drawer" aria-hidden="true">
      <ul class="mobile-nav-list">
        <li><a href="#montagem" class="mobile-nav-link">Início</a></li>
        <li><a href="#cardapio" class="mobile-nav-link">Cardápio</a></li>
        <li><a href="#como-pedir" class="mobile-nav-link">Como Pedir</a></li>
        <li><a href="#rastreio" class="mobile-nav-link" id="drawer-link-rastreio">📍 Rastrear Pedido</a></li>
        <li><a href="#clube" class="mobile-nav-link" id="drawer-link-clube" style="color: #C8A15A;">★ Clube VIP &amp; Promoções</a></li>
        <li><a href="#sobre" class="mobile-nav-link">Sobre</a></li>
        <li><a href="#contato" class="mobile-nav-link">Contato</a></li>
      </ul>

      <div class="mobile-drawer-footer">
        <button type="button" class="btn btn--primary w-full" id="btn-drawer-order">
          Fazer Pedido
        </button>
        <button type="button" class="btn-instalar-app-drawer" id="btn-instalar-app-drawer" aria-label="Instalar App Don Corleone">
          ${icone('celular', 16)}
          <span class="btn-instalar-label">Instalar App Don Corleone</span>
        </button>
      </div>
    </div>
  </header>
  `;
}

export function initHeader(config) {
  const header = document.querySelector('#site-header');
  const toggleBtn = document.querySelector('#mobile-menu-toggle');
  const drawer = document.querySelector('#mobile-drawer');
  const navLinks = document.querySelectorAll('.nav-link, .mobile-nav-link');
  const btnCart = document.querySelector('#btn-header-cart');
  const cartBadge = document.querySelector('#cart-count-badge');
  const btnOrder = document.querySelector('#btn-header-order');
  const btnDrawerOrder = document.querySelector('#btn-drawer-order');

  const progressBar = document.querySelector('#header-scroll-progress');

  // Efeito de sombra, blur e barra de progresso dourada no scroll
  const onScroll = () => {
    const scrollY = window.scrollY;
    if (scrollY > 40) {
      header?.classList.add('header--scrolled');
    } else {
      header?.classList.remove('header--scrolled');
    }

    if (progressBar) {
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const progress = maxScroll > 0 ? Math.min(1, Math.max(0, scrollY / maxScroll)) : 0;
      progressBar.style.transform = `scaleX(${progress})`;
    }
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Toggle Menu Mobile
  if (toggleBtn && drawer) {
    toggleBtn.addEventListener('click', () => {
      const isOpen = toggleBtn.getAttribute('aria-expanded') === 'true';
      toggleBtn.setAttribute('aria-expanded', String(!isOpen));
      toggleBtn.classList.toggle('is-open');
      drawer.classList.toggle('is-open');
      drawer.setAttribute('aria-hidden', String(isOpen));
      document.body.style.overflow = isOpen ? '' : 'hidden';
    });
  }

  // Smooth scroll nos links âncora
  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      const targetId = link.getAttribute('href');
      if (targetId && targetId.startsWith('#')) {
        e.preventDefault();
        
        // Fecha drawer se estiver aberta
        if (drawer?.classList.contains('is-open')) {
          toggleBtn?.classList.remove('is-open');
          toggleBtn?.setAttribute('aria-expanded', 'false');
          drawer.classList.remove('is-open');
          drawer.setAttribute('aria-hidden', 'true');
          document.body.style.overflow = '';
        }

        rolarPara(targetId, { offset: -70 });
      }
    });
  });

  // Abertura do modal de pedidos
  const abrirPedido = () => {
    if (drawer?.classList.contains('is-open')) {
      toggleBtn?.classList.remove('is-open');
      toggleBtn?.setAttribute('aria-expanded', 'false');
      drawer.classList.remove('is-open');
      drawer.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    }
    carrinho.abrirModal();
  };

  btnCart?.addEventListener('click', abrirPedido);
  btnOrder?.addEventListener('click', abrirPedido);
  btnDrawerOrder?.addEventListener('click', abrirPedido);

  // Abertura dos novos modais: Rastreio e Clube VIP
  document.querySelectorAll('#nav-link-rastreio, #drawer-link-rastreio').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      if (drawer?.classList.contains('is-open')) {
        toggleBtn?.classList.remove('is-open');
        drawer.classList.remove('is-open');
        document.body.style.overflow = '';
      }
      // Sem código: o modal mostra os pedidos recentes deste aparelho e a busca por código
      window.abrirModalRastreio?.();
    });
  });

  document.querySelectorAll('#nav-link-clube, #drawer-link-clube').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      if (drawer?.classList.contains('is-open')) {
        toggleBtn?.classList.remove('is-open');
        drawer.classList.remove('is-open');
        document.body.style.overflow = '';
      }
      window.abrirModalCliente?.();
    });
  });

  // Atualização do badge do carrinho
  window.addEventListener('carrinho-atualizado', (e) => {
    const total = e.detail?.quantidadeTotal || 0;
    if (cartBadge) {
      cartBadge.textContent = total;
      if (total > 0) {
        cartBadge.classList.add('visible');
      } else {
        cartBadge.classList.remove('visible');
      }
    }
  });

}
