/**
 * Modal de Acompanhamento de Pedido (estilo Mercado Livre)
 * Don Corleone — Pizzaria & Esfiharia
 *
 * Etapas vistas pelo cliente: Pendente > Em preparo > Enviado (ou Pronto para retirada) > Entregue.
 * Sem código, mostra os pedidos feitos neste aparelho e uma busca por código.
 */
import { buscarRastreioPedidoApi } from '../api/tracking.js';
import { formatarPreco, esc } from '../utils/dom.js';
import { pararLenis, retomarLenis } from '../utils/motion.js';
import { gerarLinkWhatsApp } from '../utils/whatsapp.js';
import { obterPedidosRecentes } from '../utils/pedidos-recentes.js';

const INTERVALO_ATUALIZACAO_MS = 15000;

let pollingInterval = null;
let codigoAtual = null;

export function renderRastreioModal() {
  return `
  <div class="rastreio-overlay" id="rastreio-modal-overlay" aria-hidden="true">
    <div class="rastreio-container" role="dialog" aria-modal="true" aria-labelledby="rastreio-titulo">
      <header class="rastreio-header">
        <div class="rastreio-header-title">
          <h3 id="rastreio-titulo">Acompanhar Pedido</h3>
          <p>Don Corleone · Cidade Alta (Cuiabá/MT)</p>
        </div>
        <button type="button" class="rastreio-close-btn" id="btn-fechar-rastreio" aria-label="Fechar acompanhamento do pedido">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </header>

      <div class="rastreio-body" id="rastreio-conteudo" aria-live="polite"></div>
    </div>
  </div>
  `;
}

export function initRastreioModal(config = {}) {
  const overlay = document.querySelector('#rastreio-modal-overlay');
  const btnFechar = document.querySelector('#btn-fechar-rastreio');
  const conteudo = document.querySelector('#rastreio-conteudo');
  const linkWhatsApp = gerarLinkWhatsApp(config);

  function pararAtualizacao() {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }

  function fechar() {
    pararAtualizacao();
    codigoAtual = null;
    overlay?.classList.remove('is-open');
    overlay?.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    retomarLenis();
  }

  function renderizarBusca(mensagemErro = '') {
    pararAtualizacao();
    codigoAtual = null;
    if (!conteudo) return;

    const recentes = obterPedidosRecentes();
    const recentesHtml = recentes.length ? `
      <div class="rastreio-recentes">
        <h4>Seus pedidos recentes</h4>
        ${recentes.map(p => `
          <button type="button" class="rastreio-recente-item" data-codigo="${esc(p.codigo)}">
            <span class="rastreio-recente-codigo">#${esc(p.codigo)}</span>
            <span class="rastreio-recente-info">
              ${new Date(p.criadoEm).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
              ${typeof p.total === 'number' ? ` · ${formatarPreco(p.total)}` : ''}
            </span>
            <span class="rastreio-recente-seta" aria-hidden="true">›</span>
          </button>
        `).join('')}
      </div>
    ` : '';

    conteudo.innerHTML = `
      ${recentesHtml}
      <form class="rastreio-busca" id="rastreio-form-busca" novalidate>
        <label for="rastreio-input-codigo">${recentes.length ? 'Ou digite o código do pedido' : 'Digite o código do seu pedido'}</label>
        <div class="rastreio-busca-linha">
          <input type="text" id="rastreio-input-codigo" class="rastreio-input" placeholder="Ex: DC-1310-74K" autocomplete="off" autocapitalize="characters" spellcheck="false" />
          <button type="submit" class="btn btn--primary">Buscar</button>
        </div>
        ${mensagemErro ? `<p class="rastreio-busca-erro">${esc(mensagemErro)}</p>` : ''}
      </form>
      <a class="rastreio-ajuda" href="${linkWhatsApp}" target="_blank" rel="noopener noreferrer">Dúvidas? Fale com a gente no WhatsApp</a>
    `;

    conteudo.querySelectorAll('.rastreio-recente-item').forEach(btn => {
      btn.addEventListener('click', () => abrir(btn.dataset.codigo));
    });
    conteudo.querySelector('#rastreio-form-busca')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const codigo = conteudo.querySelector('#rastreio-input-codigo')?.value.trim().toUpperCase();
      if (codigo) abrir(codigo);
    });
  }

  async function atualizarDados(codigo, { silencioso = false } = {}) {
    if (!conteudo) return;
    try {
      const data = await buscarRastreioPedidoApi(codigo);
      // O cliente pode ter fechado ou trocado de pedido enquanto a resposta chegava
      if (codigo !== codigoAtual) return;
      renderizarTela(data);
      if (data.is_finalizado) pararAtualizacao();
    } catch (e) {
      if (codigo !== codigoAtual) return;
      if (e.status === 404) {
        renderizarBusca(`Não encontramos o pedido ${codigo}. Confira o código e tente de novo.`);
        return;
      }
      // Numa atualização automática mantém a última tela e tenta de novo no próximo ciclo
      if (silencioso) return;
      conteudo.innerHTML = `
        <div class="rastreio-falha">
          <h4>Pedido #${esc(codigo)}</h4>
          <p>Não conseguimos carregar o andamento agora. Verifique sua internet e tente de novo.</p>
          <button type="button" class="btn btn--primary" id="btn-tentar-novamente">Tentar novamente</button>
        </div>
      `;
      document.querySelector('#btn-tentar-novamente')?.addEventListener('click', () => atualizarDados(codigo));
    }
  }

  function renderizarTela(data) {
    if (!conteudo) return;

    const timelineHtml = (data.timeline || []).map(step => {
      const stepClass = step.completed ? 'completed' : (step.current ? 'current' : '');
      return `
        <li class="timeline-step ${stepClass}">
          <div class="timeline-icon-wrap" aria-hidden="true">${step.icon}</div>
          <div class="timeline-content">
            <div class="timeline-title">
              ${esc(step.label)}
              ${step.hora ? `<span class="timeline-hora">${esc(step.hora)}</span>` : ''}
            </div>
            <div class="timeline-desc">${esc(step.sublabel)}</div>
          </div>
        </li>
      `;
    }).join('');

    const itensHtml = (data.itens || []).map(it => `
      <div class="rastreio-item-row">
        <span>${it.quantidade}x ${esc(it.nome)}${it.sabores?.length ? ` <small>(${esc(it.sabores.join(' + '))})</small>` : ''}</span>
        <strong>${formatarPreco(it.subtotal)}</strong>
      </div>
    `).join('');

    const destaqueHtml = data.is_cancelado ? `
      <div class="rastreio-cancelado">
        <strong>Pedido cancelado${data.cancelamento?.hora ? ` às ${esc(data.cancelamento.hora)}` : ''}</strong>
        ${data.cancelamento?.motivo ? `<p>Motivo: ${esc(data.cancelamento.motivo)}</p>` : ''}
        <p>Se tiver dúvidas, fale com a gente no WhatsApp.</p>
      </div>
    ` : (data.previsao ? `<div class="rastreio-previsao">${esc(data.previsao)}</div>` : '');

    const avisoPix = !data.is_cancelado && data.status === 'NOVO' && data.pagamento === 'pix'
      ? '<p class="rastreio-aviso">Assim que conferirmos seu Pix, o pedido é confirmado e entra em preparo.</p>'
      : '';

    conteudo.innerHTML = `
      <div class="rastreio-status-card ${data.is_cancelado ? 'is-cancelado' : ''}">
        <div class="rastreio-codigo-badge">#${esc(data.codigo)}</div>
        <div class="rastreio-status-atual">${esc(data.status_display)}</div>
        <div class="rastreio-status-meta">
          ${esc(data.modalidade_display)} · Feito em ${esc(data.data_criacao)}
        </div>
        ${destaqueHtml}
        ${avisoPix}
      </div>

      <ol class="rastreio-timeline ${data.is_cancelado ? 'is-cancelado' : ''}">${timelineHtml}</ol>

      <div class="rastreio-itens-box">
        <h4>Resumo do Pedido</h4>
        ${itensHtml}
        <div class="rastreio-total-row">
          <span>Total:</span>
          <span>${formatarPreco(data.total)}</span>
        </div>
      </div>

      <div class="rastreio-footer-actions">
        <a class="rastreio-ajuda" href="${linkWhatsApp}" target="_blank" rel="noopener noreferrer">Dúvidas? Fale no WhatsApp</a>
        <button type="button" class="rastreio-link-outro" id="btn-rastreio-outro">Ver outro pedido</button>
      </div>
      ${data.is_finalizado ? '' : '<p class="rastreio-rodape-nota">Esta tela atualiza sozinha.</p>'}
    `;

    document.querySelector('#btn-rastreio-outro')?.addEventListener('click', () => renderizarBusca());
  }

  function mostrarModal() {
    pararLenis();
    overlay?.classList.add('is-open');
    overlay?.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function abrir(codigo) {
    mostrarModal();
    if (!codigo) {
      renderizarBusca();
      return;
    }

    codigoAtual = codigo;
    if (conteudo) conteudo.innerHTML = '<p class="rastreio-carregando">Carregando seu pedido...</p>';
    atualizarDados(codigo);

    pararAtualizacao();
    pollingInterval = setInterval(() => {
      // Aba em segundo plano não consulta; ao voltar, atualiza na hora (visibilitychange)
      if (codigoAtual && !document.hidden) atualizarDados(codigoAtual, { silencioso: true });
    }, INTERVALO_ATUALIZACAO_MS);
  }

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && codigoAtual && pollingInterval) {
      atualizarDados(codigoAtual, { silencioso: true });
    }
  });

  btnFechar?.addEventListener('click', fechar);
  overlay?.addEventListener('click', (e) => {
    if (e.target === overlay) fechar();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay?.classList.contains('is-open')) fechar();
  });

  window.addEventListener('abrir-rastreio-pedido', (e) => {
    abrir(e.detail?.codigo);
  });

  // Link enviado no WhatsApp quando o pedido sai para entrega: ?rastreio=DC-1310-74K
  try {
    const params = new URLSearchParams(window.location.search);
    const codeParam = params.get('rastreio');
    if (codeParam) {
      setTimeout(() => abrir(codeParam), 500);
    }
  } catch (e) {}

  window.abrirModalRastreio = abrir;
}
