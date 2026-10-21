/* Painel Don Corleone: menu mobile, confirmações, avisos e atualização automática do quadro de pedidos. */
(function () {
  'use strict';

  // Menu lateral no celular
  const app = document.querySelector('.app');
  document.querySelectorAll('[data-menu-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const open = app.classList.toggle('nav-open');
      btn.setAttribute('aria-expanded', String(open));
    });
  });
  app?.addEventListener('click', (e) => {
    if (app.classList.contains('nav-open') && !e.target.closest('.sidebar') && !e.target.closest('[data-menu-toggle]')) {
      app.classList.remove('nav-open');
    }
  });

  // Confirmação em ações sensíveis: <form data-confirm="Texto">
  document.addEventListener('submit', (e) => {
    const form = e.target;
    const message = form.dataset.confirm || e.submitter?.dataset.confirm;
    if (message && !window.confirm(message)) e.preventDefault();
  });

  // Cancelamento pede o motivo (obrigatório no servidor)
  document.addEventListener('submit', (e) => {
    const form = e.target;
    if (!form.matches('[data-pede-motivo]') || e.defaultPrevented) return;
    const motivo = window.prompt('Motivo do cancelamento (o cliente pode perguntar):');
    if (!motivo || !motivo.trim()) {
      e.preventDefault();
      return;
    }
    form.querySelector('input[name="motivo"]').value = motivo.trim();
  });

  // Avisos somem sozinhos
  document.querySelectorAll('.messages .alert').forEach((el, i) => {
    setTimeout(() => { el.style.transition = 'opacity .4s'; el.style.opacity = '0'; setTimeout(() => el.remove(), 450); }, 6000 + i * 800);
  });

  // Formulário de produto: mostra a tabela de tamanhos só para pizzas
  const tipo = document.querySelector('#id_product_type');
  const tamanhos = document.querySelector('[data-tamanhos]');
  if (tipo && tamanhos) {
    const sync = () => { tamanhos.hidden = tipo.value !== 'pizza'; };
    tipo.addEventListener('change', sync);
    sync();
  }

  // WhatsApp: com o QR Code na tela, confere a conexão a cada 4 s e renova o código a cada 30 s
  const waQr = document.querySelector('[data-wa-qr]');
  if (waQr) {
    const estadoUrl = waQr.dataset.estadoUrl;
    const img = waQr.querySelector('[data-wa-qr-img]');
    const aviso = waQr.querySelector('[data-wa-qr-aviso]');
    let ultimaRenovacao = Date.now();

    const consultar = async () => {
      if (document.hidden) return;
      const renovar = Date.now() - ultimaRenovacao > 30000;
      try {
        const res = await fetch(`${estadoUrl}${renovar ? '?qr=1' : ''}`, { credentials: 'same-origin' });
        const data = await res.json();
        if (data.estado === 'open') {
          window.location.reload();
          return;
        }
        if (data.erro) {
          aviso.textContent = data.erro;
          img.classList.add('is-stale');
          return;
        }
        if (renovar && data.qr) {
          img.src = data.qr;
          img.classList.remove('is-stale');
          ultimaRenovacao = Date.now();
        }
      } catch (e) {
        aviso.textContent = 'Sem resposta do servidor. Tentando de novo...';
      }
    };
    setInterval(consultar, 4000);
  }

  // QR Codes (app do entregador e configuração do Traccar)
  document.querySelectorAll('[data-qr]').forEach((box) => {
    if (!window.qrcode) { box.textContent = 'Não foi possível gerar o QR Code. Use os dados por escrito abaixo.'; return; }
    const qr = window.qrcode(0, 'M');
    qr.addData(box.dataset.qr);
    qr.make();
    box.innerHTML = qr.createSvgTag({ cellSize: 5, margin: 3, scalable: true });
  });

  // Mapa dos entregadores: consulta as posições a cada 10 s e move os marcadores suavemente
  const mapaEl = document.querySelector('[data-mapa]');
  if (mapaEl && window.L) {
    const mapa = L.map('mapa').setView([-15.601, -56.097], 13);  // Cuiabá
    // O OpenStreetMap bloqueia imagens pedidas sem Referer; o painel (Django) usa "same-origin",
    // então só as imagens do mapa enviam o endereço do site (sem o caminho da página)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, referrerPolicy: 'strict-origin-when-cross-origin',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(mapa);
    const lista = mapaEl.querySelector('[data-mapa-lista]');
    const hora = mapaEl.querySelector('[data-mapa-hora]');
    const marcadores = new Map();
    let enquadrado = false;

    const escapar = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const tempo = (s) => {
      if (s < 60) return 'agora';
      const min = Math.round(s / 60);
      return min < 60 ? `há ${min} min` : `há ${Math.floor(min / 60)} h ${min % 60} min`;
    };
    const icone = (e) => L.divIcon({
      className: '',
      html: `<span class="map-pin ${e.na_rua ? 'is-route' : ''} ${e.parado ? 'is-stale' : ''}" title="${escapar(e.nome)}">${escapar(e.iniciais)}</span><span class="map-pin-label">${escapar(e.nome)}</span>`,
      iconSize: [36, 36], iconAnchor: [18, 18],
    });
    const mover = (marker, destino) => {
      const origem = marker.getLatLng();
      const inicio = performance.now();
      const passo = (agora) => {
        const t = Math.min(1, (agora - inicio) / 1200);
        marker.setLatLng([origem.lat + (destino[0] - origem.lat) * t, origem.lng + (destino[1] - origem.lng) * t]);
        if (t < 1) requestAnimationFrame(passo);
      };
      requestAnimationFrame(passo);
    };

    const atualizar = async () => {
      if (document.hidden) return;
      let dados;
      try {
        const res = await fetch(mapaEl.dataset.posicoesUrl, { credentials: 'same-origin' });
        if (res.redirected || !res.ok) return;
        dados = await res.json();
      } catch (err) {
        hora.textContent = 'Sem conexão com o servidor';
        return;
      }
      const vistos = new Set();
      dados.entregadores.forEach((e) => {
        if (e.lat === null) return;
        vistos.add(e.id);
        const pos = [e.lat, e.lon];
        const atual = marcadores.get(e.id);
        if (atual) {
          atual.setIcon(icone(e));
          mover(atual, pos);
        } else {
          marcadores.set(e.id, L.marker(pos, { icon: icone(e) }).addTo(mapa));
        }
      });
      marcadores.forEach((m, id) => { if (!vistos.has(id)) { m.remove(); marcadores.delete(id); } });
      if (!enquadrado && marcadores.size) {
        mapa.fitBounds(L.featureGroup([...marcadores.values()]).getBounds().pad(0.3), { maxZoom: 15 });
        enquadrado = true;
      }

      lista.innerHTML = dados.entregadores.length ? dados.entregadores.map((e) => {
        let sinal;
        if (e.lat !== null) sinal = `${e.parado ? `parado, última posição ${tempo(e.ha_segundos)}` : tempo(e.ha_segundos)}${e.bateria !== null ? ` · bateria ${e.bateria}%` : ''}`;
        else if (!e.tem_app) sinal = 'App não configurado';
        else sinal = dados.loja_no_horario || e.na_rua ? 'Sem sinal do Traccar' : 'Fora do horário: não rastreado';
        return `<div class="map-row">
            <button type="button" class="map-focus" data-id="${e.id}" ${e.lat === null ? 'disabled' : ''} aria-label="Mostrar ${escapar(e.nome)} no mapa">
              <span class="map-pin ${e.na_rua ? 'is-route' : ''}">${escapar(e.iniciais)}</span>
              <span><strong>${escapar(e.nome)}</strong><br><span class="muted small">${e.na_rua ? `${e.na_rua} na bag` : 'Na loja'} · ${escapar(sinal)}</span></span>
            </button>
            <a href="${e.detalhe}" class="small">Ver</a>
          </div>`;
      }).join('') : '<p class="muted small">Ninguém marcado como trabalhando hoje.</p>';
      hora.textContent = `Atualizado às ${new Date().toLocaleTimeString('pt-BR')}`;
    };
    lista.addEventListener('click', (e) => {
      const row = e.target.closest('.map-focus');
      const marker = row && marcadores.get(row.dataset.id);
      if (marker) mapa.setView(marker.getLatLng(), 16);
    });
    atualizar();
    setInterval(atualizar, 10000);
    document.addEventListener('visibilitychange', atualizar);
  }

  // Quadro de pedidos: atualiza a cada 15 s e toca um aviso quando chega pedido novo
  const board = document.querySelector('[data-quadro-url]');
  if (!board) return;

  const url = board.dataset.quadroUrl;
  const baseTitle = document.title;
  let known = new Set([...board.querySelectorAll('[data-pedido-id]')].map((el) => el.dataset.pedidoId));
  let audioCtx = null;

  function beep() {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      [0, 0.22].forEach((delay) => {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.frequency.value = 880;
        gain.gain.setValueAtTime(0.0001, audioCtx.currentTime + delay);
        gain.gain.exponentialRampToValueAtTime(0.25, audioCtx.currentTime + delay + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + delay + 0.18);
        osc.connect(gain).connect(audioCtx.destination);
        osc.start(audioCtx.currentTime + delay);
        osc.stop(audioCtx.currentTime + delay + 0.2);
      });
    } catch (e) { /* som indisponível */ }
  }
  // Navegadores só liberam som depois de uma interação
  document.addEventListener('click', () => { if (!audioCtx) { try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {} } }, { once: true });

  function updateTitle() {
    const novos = Number(board.querySelector('[data-qtd-novos]')?.dataset.qtdNovos || 0);
    document.title = novos ? `(${novos}) ${baseTitle}` : baseTitle;
  }

  async function refresh() {
    if (document.querySelector('.order-actions form:focus-within')) return;
    try {
      const res = await fetch(url, { headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' });
      if (res.redirected || !res.ok) return;
      board.innerHTML = await res.text();
      const ids = [...board.querySelectorAll('[data-pedido-id]')];
      let arrived = false;
      ids.forEach((el) => {
        if (!known.has(el.dataset.pedidoId)) {
          el.classList.add('is-new-arrival');
          if (el.dataset.status === 'NOVO') arrived = true;
        }
      });
      known = new Set(ids.map((el) => el.dataset.pedidoId));
      if (arrived) beep();
      updateTitle();
      board.dataset.falhou = '';
    } catch (e) {
      board.dataset.falhou = '1';
    }
  }

  updateTitle();
  setInterval(refresh, 15000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
})();
