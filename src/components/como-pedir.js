import { esc } from '../utils/dom.js';

export function renderComoPedir(config) {
  const dados = config.textos?.comoPedir || {};
  const passos = dados.passos || [
    {
      numero: "01",
      titulo: "Escolha seus sabores",
      descricao: "Explore o cardápio e selecione o que deseja pedir."
    },
    {
      numero: "02",
      titulo: "Informe os detalhes",
      descricao: "Escolha entrega ou retirada, preencha seus dados e informe a forma de pagamento."
    },
    {
      numero: "03",
      titulo: "Envie e acompanhe",
      descricao: "Confira o resumo, envie e acompanhe o pedido aqui no site."
    }
  ];

  const passosHtml = passos.map((passo, idx) => `
    <div class="passo-card" data-step="${idx + 1}">
      <div class="passo-numero-wrap">
        <span class="passo-numero">${esc(passo.numero)}</span>
      </div>
      <div class="passo-conteudo">
        <h3 class="passo-titulo">${esc(passo.titulo)}</h3>
        <p class="passo-desc">${esc(passo.descricao)}</p>
      </div>
    </div>
  `).join('');

  return `
  <section id="como-pedir" class="secao-como-pedir" aria-labelledby="como-pedir-titulo">
    <div class="container">
      <div class="text-center">
        <span class="section-tag">Praticidade</span>
        <h2 id="como-pedir-titulo" class="section-title">${esc(dados.titulo || 'Como Fazer Seu Pedido')}</h2>
        <p class="section-subtitle mb-8">
          ${esc(dados.subtitulo || 'Três etapas simples para saborear a Don Corleone.')}
        </p>
      </div>

      <div class="passos-grid">
        ${passosHtml}
      </div>

      <div class="como-pedir-nota text-center mt-8">
        <p class="text-muted text-sm">
          ${esc(dados.nota || 'Dúvidas? Fale com a gente no WhatsApp. Avisamos por lá quando seu pedido sair para entrega.')}
        </p>
      </div>
    </div>
  </section>
  `;
}

export function initComoPedir(config) {
  // Inicialização de passos
}
