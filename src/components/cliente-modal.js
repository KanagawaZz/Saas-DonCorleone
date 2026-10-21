/**
 * Modal de Cadastro e Login de Clientes
 * Permite aos clientes se cadastrarem para participar de promoções especiais e cupons VIP.
 */
import { cadastrarClienteApi, loginClienteApi, logoutCliente, obterUsuarioLogado } from '../api/auth.js';
import { pararLenis, retomarLenis } from '../utils/motion.js';

export function renderClienteModal() {
  return `
  <div class="cliente-modal-overlay" id="cliente-modal-overlay" aria-hidden="true">
    <div class="cliente-modal-container" role="dialog" aria-modal="true" aria-labelledby="cliente-titulo">
      <header class="cliente-modal-header">
        <h3 id="cliente-titulo">Clube Don Corleone</h3>
        <button type="button" class="rastreio-close-btn" id="btn-fechar-cliente-modal" aria-label="Fechar">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </header>

      <div class="cliente-modal-tabs">
        <button type="button" class="cliente-tab-btn active" id="tab-btn-cadastro">Cadastre-se</button>
        <button type="button" class="cliente-tab-btn" id="tab-btn-login">Já sou Cliente</button>
      </div>

      <div class="cliente-modal-body">
        <div class="cliente-alerta" id="cliente-alerta-box"></div>

        <!-- Formulário de Cadastro -->
        <form id="form-cliente-cadastro">
          <div style="font-size:0.85rem; color:#A89F91; margin-bottom:12px;">
            Cadastre-se para liberar cupons exclusivos, promoções e rastreio facilitado dos seus pedidos!
          </div>
          <div class="cliente-form-group">
            <label for="cad-nome">Seu Nome Completo *</label>
            <input type="text" id="cad-nome" class="cliente-input" placeholder="Ex: Kayron Eduardo" required />
          </div>
          <div class="cliente-form-group">
            <label for="cad-whats">WhatsApp com DDD *</label>
            <input type="tel" id="cad-whats" class="cliente-input" placeholder="Ex: 65 99999-9999" required />
          </div>
          <div class="cliente-form-group">
            <label for="cad-bairro">Seu Bairro (Cuiabá / VG)</label>
            <input type="text" id="cad-bairro" class="cliente-input" placeholder="Ex: Cidade Alta" />
          </div>
          <div class="cliente-form-group">
            <label for="cad-senha">Crie uma Senha (mín. 6 dígitos) *</label>
            <input type="password" id="cad-senha" class="cliente-input" placeholder="••••••••" minlength="6" required />
          </div>
          <button type="submit" class="cliente-btn-submit" id="btn-submit-cadastro">Criar Meu Cadastro VIP</button>
        </form>

        <!-- Formulário de Login -->
        <form id="form-cliente-login" style="display: none;">
          <div class="cliente-form-group">
            <label for="login-whats">WhatsApp ou Usuário</label>
            <input type="text" id="login-whats" class="cliente-input" placeholder="Seu WhatsApp" required />
          </div>
          <div class="cliente-form-group">
            <label for="login-senha">Sua Senha</label>
            <input type="password" id="login-senha" class="cliente-input" placeholder="••••••••" required />
          </div>
          <button type="submit" class="cliente-btn-submit" id="btn-submit-login">Entrar</button>
        </form>

        <!-- Painel se já estiver logado -->
        <div id="cliente-logado-box" style="display: none; text-align: center; padding: 10px 0;">
          <h4 style="color:#C8A15A; margin: 0 0 6px;">Olá, <span id="logado-nome"></span>! 👋</h4>
          <p style="font-size: 0.9rem; color: #A89F91;">Você está conectado ao Clube Don Corleone e elegível às promoções especiais.</p>
          <button type="button" class="btn btn--outline" id="btn-cliente-sair" style="margin-top: 14px; padding: 8px 18px;">
            Sair da Conta
          </button>
        </div>
      </div>
    </div>
  </div>
  `;
}

export function initClienteModal() {
  const overlay = document.querySelector('#cliente-modal-overlay');
  const btnFechar = document.querySelector('#btn-fechar-cliente-modal');
  const tabCad = document.querySelector('#tab-btn-cadastro');
  const tabLog = document.querySelector('#tab-btn-login');
  const formCad = document.querySelector('#form-cliente-cadastro');
  const formLog = document.querySelector('#form-cliente-login');
  const logadoBox = document.querySelector('#cliente-logado-box');
  const logadoNome = document.querySelector('#logado-nome');
  const alertaBox = document.querySelector('#cliente-alerta-box');
  const btnSair = document.querySelector('#btn-cliente-sair');

  function fechar() {
    overlay?.classList.remove('is-open');
    overlay?.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    retomarLenis();
  }

  function mostrarAlerta(msg, tipo = 'erro') {
    if (!alertaBox) return;
    alertaBox.textContent = msg;
    alertaBox.className = `cliente-alerta ${tipo}`;
    alertaBox.style.display = 'block';
  }

  function alternarAba(aba) {
    if (alertaBox) alertaBox.style.display = 'none';
    if (aba === 'cadastro') {
      tabCad?.classList.add('active');
      tabLog?.classList.remove('active');
      if (formCad) formCad.style.display = 'block';
      if (formLog) formLog.style.display = 'none';
    } else {
      tabLog?.classList.add('active');
      tabCad?.classList.remove('active');
      if (formLog) formLog.style.display = 'block';
      if (formCad) formCad.style.display = 'none';
    }
  }

  function atualizarEstadoAutenticacao() {
    const user = obterUsuarioLogado();
    if (user) {
      if (formCad) formCad.style.display = 'none';
      if (formLog) formLog.style.display = 'none';
      if (tabCad) tabCad.parentElement.style.display = 'none';
      if (logadoBox) logadoBox.style.display = 'block';
      if (logadoNome) logadoNome.textContent = user.first_name || user.username;
    } else {
      if (tabCad) tabCad.parentElement.style.display = 'flex';
      if (logadoBox) logadoBox.style.display = 'none';
      alternarAba('cadastro');
    }
  }

  function abrir() {
    pararLenis();
    atualizarEstadoAutenticacao();
    overlay?.classList.add('is-open');
    overlay?.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  tabCad?.addEventListener('click', () => alternarAba('cadastro'));
  tabLog?.addEventListener('click', () => alternarAba('login'));
  btnFechar?.addEventListener('click', fechar);
  overlay?.addEventListener('click', (e) => {
    if (e.target === overlay) fechar();
  });

  formCad?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const nome = document.querySelector('#cad-nome')?.value?.trim();
    const whats = document.querySelector('#cad-whats')?.value?.trim();
    const bairro = document.querySelector('#cad-bairro')?.value?.trim();
    const senha = document.querySelector('#cad-senha')?.value;

    try {
      const res = await cadastrarClienteApi({
        name: nome,
        whatsapp: whats,
        neighborhood: bairro,
        password: senha
      });
      mostrarAlerta(res.message || "Cadastro realizado com sucesso!", "sucesso");
      setTimeout(() => {
        atualizarEstadoAutenticacao();
        fechar();
      }, 1500);
    } catch (err) {
      mostrarAlerta(err.message || "Erro ao realizar cadastro.", "erro");
    }
  });

  formLog?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const whats = document.querySelector('#login-whats')?.value?.trim();
    const senha = document.querySelector('#login-senha')?.value;

    try {
      const res = await loginClienteApi(whats, senha);
      mostrarAlerta("Login realizado com sucesso!", "sucesso");
      setTimeout(() => {
        atualizarEstadoAutenticacao();
        fechar();
      }, 1000);
    } catch (err) {
      mostrarAlerta(err.message || "Erro ao realizar login.", "erro");
    }
  });

  btnSair?.addEventListener('click', () => {
    logoutCliente();
    atualizarEstadoAutenticacao();
    mostrarAlerta("Você saiu da conta.", "sucesso");
  });

  window.addEventListener('abrir-modal-cliente', abrir);
  window.abrirModalCliente = abrir;
}
