import './styles/main.css';

import { siteConfig } from './data/site.config.js';
import dadosCardapio from './data/cardapio.json';
import dadosDepoimentos from './data/depoimentos.json';

import { carregarDadosDoBanco } from './api/dados-site.js';
import { inicializarMotion } from './utils/motion.js';
import { inicializarPWA } from './utils/pwa.js';

// Componentes
import { renderHeader, initHeader } from './components/header.js';
import { renderBannerPromocao, initBannerPromocao } from './components/banner-promocao.js';
import { renderMontagem, initMontagem } from './components/montagem/montagem.js';
import { initStatusAberto } from './components/status-aberto.js';
import { renderMarquee, initMarquee } from './components/marquee.js';
import { renderCardapio, initCardapio } from './components/cardapio.js';
import { renderPizzaCustomizerModal, initPizzaCustomizerModal } from './components/pizza-customizer-modal.js';
import { renderCarrinhoModal, initCarrinhoModal } from './components/carrinho-modal.js';
import { renderComoPedir, initComoPedir } from './components/como-pedir.js';
import { renderSobre, initSobre } from './components/sobre.js';
import { renderGaleria, initGaleria } from './components/galeria.js';
import { renderDepoimentos, initDepoimentos } from './components/depoimentos.js';
import { renderContato, initContato } from './components/contato.js';
import { renderFooter, initFooter } from './components/footer.js';
import { renderBarraPedido, initBarraPedido } from './components/barra-pedido.js';
import { renderRastreioModal, initRastreioModal } from './components/rastreio-modal.js';
import { renderClienteModal, initClienteModal } from './components/cliente-modal.js';

function montarAplicacao() {
  const app = document.querySelector('#app');
  if (!app) return;

  // Montagem da árvore HTML usando os dados
  const html = `
    <a href="#montagem" class="skip-link">Pular para o conteúdo principal</a>
    ${renderHeader(siteConfig)}
    ${renderBannerPromocao(siteConfig)}
    <main id="main-content">
      ${renderMontagem(siteConfig)}
      ${renderMarquee(siteConfig)}
      ${renderCardapio(siteConfig, dadosCardapio)}
      ${renderComoPedir(siteConfig)}
      ${renderSobre(siteConfig)}
      ${renderGaleria(siteConfig)}
      ${renderDepoimentos(siteConfig, dadosDepoimentos)}
      ${renderContato(siteConfig)}
    </main>
    ${renderFooter(siteConfig)}
    ${renderBarraPedido(siteConfig)}
    ${renderPizzaCustomizerModal(siteConfig)}
    ${renderCarrinhoModal(siteConfig)}
    ${renderRastreioModal()}
    ${renderClienteModal()}
  `;

  app.innerHTML = html;

  // Inicializa animações e interações
  inicializarMotion();

  initHeader(siteConfig);
  initBannerPromocao(siteConfig);
  initStatusAberto(siteConfig);
  initMontagem(siteConfig);
  initMarquee(siteConfig);
  initCardapio(siteConfig, dadosCardapio);
  initPizzaCustomizerModal(siteConfig);
  initCarrinhoModal(siteConfig);
  initRastreioModal(siteConfig);
  initClienteModal();
  initComoPedir(siteConfig);
  initSobre(siteConfig);
  initGaleria(siteConfig);
  initDepoimentos(siteConfig);
  initContato(siteConfig);
  initFooter(siteConfig);
  initBarraPedido(siteConfig);
  inicializarPWA();
}


// Busca cardápio, taxas, horários e promoção do painel antes de montar a página
// (com os arquivos locais como reserva se o backend não responder)
const dadosProntos = carregarDadosDoBanco();

async function iniciar() {
  await dadosProntos;
  montarAplicacao();
}

// Inicializa quando o DOM estiver pronto
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', iniciar);
} else {
  iniciar();
}
