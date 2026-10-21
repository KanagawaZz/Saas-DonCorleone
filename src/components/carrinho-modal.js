/**
 * Modal & Drawer de Carrinho e Checkout Integrado - Don Corleone
 * 
 * Funcionalidades evoluídas:
 * 1. Taxa de entrega calculada por bairro (Cuiabá e Várzea Grande) ou a confirmar
 * 2. Envio do pedido direto para o sistema (o código DC-DDMM-XXX vem do backend)
 * 3. Sem WhatsApp no fluxo do pedido: a pizzaria confirma pelo painel
 * 4. Tela pós-envio com código, chave Pix (copiar com 1 clique) e acesso ao acompanhamento
 * 5. Bloqueio automático de pedidos quando fechado ou após o horário de corte (22:30)
 * 6. Autopreenchimento para quem recompra (localStorage) com opção de limpar
 * 7. Aplicação de desconto de promoções ativas no fuso de Cuiabá
 */

import { carrinho } from '../utils/carrinho.js';
import { formatarPreco, esc, extrairNumeroMoeda } from '../utils/dom.js';
import { icone } from '../utils/icons.js';
import { formatarTituloPizza } from '../utils/calculo-pizza.js';
import { gerarLinkWhatsApp } from '../utils/whatsapp.js';
import { registrarPedidoRecente } from '../utils/pedidos-recentes.js';
import { pararLenis, retomarLenis } from '../utils/motion.js';
import bairrosLista from '../data/bairros.json';
import { calcularTaxaEntrega } from '../utils/entrega.js';
import { obterStatusFuncionamento } from '../utils/horario.js';
import { obterPromocaoAtiva } from '../utils/promocao.js';
import { ITENS_COMPRE_JUNTO } from '../data/compre-junto.js';
import { criarPedidoApi } from '../api/orders.js';

const STORAGE_CLIENTE_KEY = 'don_corleone_cliente_v1';


export function renderCarrinhoModal(config) {
  const tempoRetirada = config?.operacional?.tempoRetirada || config?.pagamento?.tempoMedioRetirada || '20 a 35 min';

  return `
  <div class="pedido-modal-overlay" id="pedido-modal-overlay" data-lenis-prevent="true" aria-hidden="true">
    <div class="pedido-modal-container" id="pedido-modal-container" data-lenis-prevent="true" role="dialog" aria-modal="true" aria-labelledby="modal-titulo">
      
      <!-- Cabeçalho do Modal -->
      <header class="pedido-modal-header">
        <div class="pedido-modal-title-group">
          <img src="${config.marca?.brasaoUrl || '/images/brand/brasao.svg'}" alt="Don Corleone" class="pedido-header-brasao" width="28" height="28" />
          <div>
            <h2 id="modal-titulo" class="pedido-modal-title">Seu Pedido</h2>
            <p class="pedido-modal-subtitle">Don Corleone · Pizzaria &amp; Esfiharia Cidade Alta (Cuiabá/MT)</p>
          </div>
        </div>
        <button type="button" class="pedido-modal-close" id="btn-fechar-modal" aria-label="Fechar janela de pedido">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </header>

      <!-- Corpo do Modal com Scroll -->
      <div class="pedido-modal-body" id="pedido-modal-body" data-lenis-prevent="true" tabindex="0">
        
        <!-- Banner de Alerta se a Cantina estiver Fechada ou após Corte -->
        <div class="aviso-fechado-checkout" id="aviso-fechado-checkout" style="display: none;">
          <div class="aviso-fechado-icon">${icone('alerta', 26)}</div>
          <div class="aviso-fechado-textos">
            <strong>Pizzaria Fechada para Novos Pedidos</strong>
            <p id="aviso-fechado-mensagem">Consulte o cardápio e valores livremente. Os pedidos só podem ser finalizados quando a pizzaria estiver aberta.</p>
          </div>
        </div>

        <!-- Alerta de Carrinho Vazio -->
        <div class="carrinho-vazio-aviso" id="carrinho-vazio-aviso" style="display: none;">
          <div class="vazio-icon-wrap">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="8" cy="21" r="1"></circle>
              <circle cx="19" cy="21" r="1"></circle>
              <path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"></path>
            </svg>
          </div>
          <h3>Seu carrinho está vazio</h3>
          <p>Monte uma pizza saborosa com até 3 sabores ou escolha suas esfihas no cardápio.</p>
          <button type="button" class="btn btn--primary btn--voltar-cardapio" id="btn-ir-cardapio">
            Explorar Cardápio
          </button>
        </div>

        <!-- Conteúdo do Formulário quando há itens -->
        <div id="carrinho-conteudo-ativo">
          
          <!-- SEÇÃO 1: Itens Selecionados no Carrinho -->
          <section class="pedido-secao secao-itens">
            <div class="secao-header-flex">
              <h3 class="pedido-secao-titulo">
                <span class="secao-num">1</span>
                Itens no Carrinho
              </h3>
              <button type="button" class="btn-link-add-mais" id="btn-add-mais">
                + Adicionar mais itens
              </button>
            </div>
            
            <div class="pedido-itens-lista" id="pedido-itens-lista">
              <!-- Renderizado dinamicamente -->
            </div>

            <div class="pedido-subtotal-bar">
              <span class="subtotal-label">Subtotal dos produtos:</span>
              <span class="subtotal-valor" id="subtotal-produtos-display">R$ 0,00</span>
            </div>
          </section>

          <!-- SEÇÃO COMPRE JUNTO / UPSELL -->
          <section class="pedido-secao secao-compre-junto" id="secao-compre-junto">
            <div class="compre-junto-header">
              <div class="compre-junto-title-wrap">
                <span class="compre-junto-tag">Compre Junto</span>
                <h4 class="compre-junto-titulo">Bebidas e Sobremesas Rápidas</h4>
              </div>
              <span class="compre-junto-dica">Adicione com 1 clique</span>
            </div>
            
            <div class="compre-junto-slider" id="compre-junto-slider" tabindex="0" aria-label="Sugestões de bebidas e sobremesas">
              <!-- Renderizado dinamicamente -->
            </div>
          </section>

          <!-- SEÇÃO 2: Dados do Cliente -->
          <section class="pedido-secao secao-cliente">
            <div class="secao-header-flex">
              <h3 class="pedido-secao-titulo">
                <span class="secao-num">2</span>
                Seus Dados
              </h3>
              <button type="button" class="btn-limpar-dados" id="btn-limpar-dados" style="display: none;" title="Limpar dados salvos neste aparelho">
                Limpar meus dados salvos
              </button>
            </div>
            
            <div class="form-grid-2">
              <div class="form-campo">
                <label for="cliente-nome" class="form-label">
                  Nome completo <span class="campo-obrigatorio">*</span>
                </label>
                <input type="text" id="cliente-nome" name="cliente_nome" class="form-input" placeholder="Ex: João Silva" required autocomplete="name" />
                <span class="form-erro" id="erro-cliente-nome"></span>
              </div>

              <div class="form-campo">
                <label for="cliente-telefone" class="form-label">
                  Telefone / WhatsApp <span class="campo-obrigatorio">*</span>
                </label>
                <input type="tel" id="cliente-telefone" name="cliente_telefone" class="form-input" placeholder="(65) 99999-9999" required autocomplete="tel" />
                <span class="form-erro" id="erro-cliente-telefone"></span>
              </div>
            </div>

            <!-- Opção de Lembrar Dados para Recompra -->
            <div class="salvar-dados-wrap mt-3">
              <label class="checkbox-lembrar-label">
                <input type="checkbox" id="lembrar-dados-check" checked />
                <span>Lembrar meus dados neste aparelho para compras futuras</span>
              </label>
            </div>
          </section>

          <!-- SEÇÃO 3: Modalidade de Atendimento -->
          <section class="pedido-secao secao-modalidade">
            <h3 class="pedido-secao-titulo">
              <span class="secao-num">3</span>
              Modalidade do Pedido
            </h3>
            
            <div class="modalidade-selector" role="radiogroup" aria-label="Escolha a forma de recebimento">
              <label class="modalidade-card active" id="modalidade-card-entrega">
                <input type="radio" name="modalidade_tipo" value="entrega" checked class="sr-only" />
                <div class="modalidade-card-inner">
                  <div class="modalidade-icon-box">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M5 18H3c-.6 0-1-.4-1-1V7c0-.6.4-1 1-1h10c.6 0 1 .4 1 1v11"/>
                      <path d="M14 9h4l4 4v4c0 .6-.4 1-1 1h-2"/>
                      <circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>
                    </svg>
                  </div>
                  <div class="modalidade-textos">
                    <span class="modalidade-titulo">Entrega (Delivery)</span>
                    <span class="modalidade-desc">Receba quentinha com motoboy próprio</span>
                  </div>
                  <div class="modalidade-check-indicator"></div>
                </div>
              </label>

              <label class="modalidade-card" id="modalidade-card-retirada">
                <input type="radio" name="modalidade_tipo" value="retirada" class="sr-only" />
                <div class="modalidade-card-inner">
                  <div class="modalidade-icon-box">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/>
                      <path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>
                    </svg>
                  </div>
                  <div class="modalidade-textos">
                    <span class="modalidade-titulo">Retirada no Balcão</span>
                    <span class="modalidade-desc">Unidade Cidade Alta (Taxa R$ 0) · ${tempoRetirada}</span>
                  </div>
                  <div class="modalidade-check-indicator"></div>
                </div>
              </label>
            </div>

            <!-- Bloco Condicional: Campos de Endereço para Entrega -->
            <div class="condicional-bloco" id="bloco-endereco-entrega">
              
              <!-- CEP com Busca Automática no ViaCEP -->
              <div class="form-campo form-campo-cep mb-3">
                <label for="entrega-cep" class="form-label">
                  CEP <span class="campo-dica">(preenche rua e bairro automaticamente)</span>
                </label>
                <div class="cep-input-group">
                  <input 
                    type="tel" 
                    id="entrega-cep" 
                    name="entrega_cep" 
                    class="form-input" 
                    placeholder="Ex: 78030-409" 
                    maxlength="9" 
                    autocomplete="postal-code" 
                  />
                  <button type="button" class="btn-cep-consultar" id="btn-cep-consultar" title="Buscar endereço pelo CEP">
                    <svg class="cep-icon-search" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    <span id="cep-status-texto">Buscar</span>
                  </button>
                </div>
                <span class="form-cep-feedback" id="cep-feedback-msg"></span>
              </div>

              <!-- Bairro de Entrega com Busca por Digitação (Searchable Combobox) -->
              <div class="form-campo mt-3 bairro-search-wrapper" id="bairro-search-wrapper">
                <label for="entrega-bairro-input" class="form-label">
                  Bairro de Entrega <span class="campo-obrigatorio">*</span>
                </label>
                <div class="bairro-input-container" id="bairro-input-container">
                  <input 
                    type="text" 
                    id="entrega-bairro-input" 
                    name="entrega_bairro_input" 
                    class="form-input" 
                    placeholder="Digite seu bairro (ex: Cidade Alta, Goiabeiras...)" 
                    autocomplete="off" 
                    required 
                  />
                  <button type="button" class="btn-trocar-bairro" id="btn-trocar-bairro" style="display: none;" title="Trocar bairro">
                    Trocar
                  </button>
                  <button type="button" class="btn-dropdown-arrow" id="btn-dropdown-arrow" aria-label="Abrir lista de bairros">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                  </button>
                </div>

                <!-- Dropdown Flutuante de Bairros Filtrados -->
                <div class="bairros-dropdown-list" id="bairros-dropdown-list" style="display: none;"></div>

                <input type="hidden" id="entrega-bairro-hidden" value="" />
                <span class="form-erro" id="erro-entrega-bairro"></span>
              </div>

              <!-- Campo que aparece se o usuário escolher "Outro bairro" -->
              <div class="form-campo mt-2" id="campo-outro-bairro" style="display: none;">
                <label for="entrega-bairro-outro" class="form-label">
                  Nome do seu bairro <span class="campo-obrigatorio">*</span>
                </label>
                <input type="text" id="entrega-bairro-outro" name="entrega_bairro_outro" class="form-input" placeholder="Digite o nome do seu bairro..." />
                <span class="form-help-subtle">A taxa para este bairro será confirmada pela pizzaria junto com o pedido.</span>
              </div>

              <!-- Alerta Dinâmico da Taxa do Bairro -->
              <div class="aviso-taxa-entrega mt-3" id="aviso-taxa-dinamica">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <span id="texto-taxa-dinamica"><strong>Taxa de entrega:</strong> informe o CEP ou digite seu bairro acima para calcular.</span>
              </div>

              <div class="form-grid-3 mt-3">
                <div class="form-campo grid-col-2">
                  <label for="entrega-rua" class="form-label">
                    Rua / Avenida <span class="campo-obrigatorio">*</span>
                  </label>
                  <input type="text" id="entrega-rua" name="entrega_rua" class="form-input" placeholder="Ex: Av. Brasil" required />
                  <span class="form-erro" id="erro-entrega-rua"></span>
                </div>

                <div class="form-campo">
                  <label for="entrega-numero" class="form-label">
                    Número <span class="campo-obrigatorio">*</span>
                  </label>
                  <input type="text" id="entrega-numero" name="entrega_numero" class="form-input" placeholder="Ex: 2055" required />
                  <span class="form-erro" id="erro-entrega-numero"></span>
                </div>
              </div>

              <div class="form-grid-2 mt-3">
                <div class="form-campo">
                  <label for="entrega-complemento" class="form-label">Complemento (opcional)</label>
                  <input type="text" id="entrega-complemento" name="entrega_complemento" class="form-input" placeholder="Ex: Apto 402, Bloco B" />
                </div>

                <div class="form-campo">
                  <label for="entrega-referencia" class="form-label">Ponto de referência (opcional)</label>
                  <input type="text" id="entrega-referencia" name="entrega_referencia" class="form-input" placeholder="Ex: Próximo à praça / mercado" />
                </div>
              </div>

              <div class="form-campo mt-3">
                <label for="entrega-cidade" class="form-label">Cidade / Região</label>
                <input type="text" id="entrega-cidade" name="entrega_cidade" class="form-input" value="Cuiabá / Várzea Grande — MT" readonly />
              </div>
            </div>

            <!-- Bloco Condicional: Informações de Retirada no Balcão -->
            <div class="condicional-bloco" id="bloco-info-retirada" style="display: none;">
              <div class="balcao-info-box">
                <div class="balcao-badge">Retirada no Balcão · Taxa Grátis</div>
                <h4>Unidade Cidade Alta</h4>
                <p><strong>Endereço:</strong> Avenida Brasil, 2055, Cidade Alta, Cuiabá - MT (CEP 78030-409)</p>
                <p class="mt-1"><strong>Expediente:</strong> Seg a Qui: 17h30 às 23h00 · Sex e Dom: 17h30 às 23h15 · Sáb: 17h30 às 23h30</p>
                <div class="balcao-tempo-box">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                  </svg>
                  <span><strong>Tempo médio até ficar pronto:</strong> ${tempoRetirada}</span>
                </div>
                <div class="form-campo mt-3">
                  <label for="retirada-horario" class="form-label">Horário pretendido para retirada (opcional)</label>
                  <input type="text" id="retirada-horario" name="retirada_horario" class="form-input" placeholder="Ex: Em 30 minutos / Às 20:30" />
                </div>
              </div>
            </div>
          </section>

          <!-- SEÇÃO 4: Forma de Pagamento -->
          <section class="pedido-secao secao-pagamento">
            <h3 class="pedido-secao-titulo">
              <span class="secao-num">4</span>
              Forma de Pagamento
            </h3>

            <div class="pagamento-options-grid">
              <label class="pagamento-opcao active">
                <input type="radio" name="forma_pagamento" value="pix" checked class="sr-only" />
                <div class="pagamento-opcao-box">
                  <svg class="pag-icon" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                    <path d="M12 2 4 10l8 8 8-8-8-8zm0 4.24 3.76 3.76L12 13.76 8.24 10 12 6.24z"/>
                  </svg>
                  <span class="pag-nome">Pix</span>
                </div>
              </label>

              <label class="pagamento-opcao">
                <input type="radio" name="forma_pagamento" value="dinheiro" class="sr-only" />
                <div class="pagamento-opcao-box">
                  <svg class="pag-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="2" y="6" width="20" height="12" rx="2"></rect>
                    <circle cx="12" cy="12" r="2"></circle>
                    <path d="M6 12h.01M18 12h.01"></path>
                  </svg>
                  <span class="pag-nome">Dinheiro</span>
                </div>
              </label>

              <label class="pagamento-opcao">
                <input type="radio" name="forma_pagamento" value="cartao_credito" class="sr-only" />
                <div class="pagamento-opcao-box">
                  <svg class="pag-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
                    <line x1="1" y1="10" x2="23" y2="10"></line>
                  </svg>
                  <span class="pag-nome">Crédito</span>
                </div>
              </label>

              <label class="pagamento-opcao">
                <input type="radio" name="forma_pagamento" value="cartao_debito" class="sr-only" />
                <div class="pagamento-opcao-box">
                  <svg class="pag-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
                    <line x1="1" y1="10" x2="23" y2="10"></line>
                  </svg>
                  <span class="pag-nome">Débito</span>
                </div>
              </label>
            </div>

            <!-- Bandeiras de Cartão Aceitas na Entrega -->
            <div class="pagamento-bandeiras-nota mt-2">
              <span class="bandeiras-icone">${icone('cartao', 18)}</span>
              <span>Bandeiras aceitas na maquininha na entrega: <strong>Visa, Mastercard, American Express e Elo</strong></span>
            </div>

            <!-- Bloco Informativo de Pix -->
            <div class="condicional-bloco mt-3" id="bloco-aviso-pix">
              <div class="pix-aviso-box">
                <span class="pix-badge-pill">Atenção ao Pix</span>
                <p>A chave Pix oficial (<strong>${config.pagamento?.pix?.chave || '65993605364'}</strong>) aparece na tela após o envio. O pedido entra em preparo <strong>assim que a pizzaria conferir o pagamento</strong>.</p>
              </div>
            </div>

            <!-- Bloco Condicional de Troco para Dinheiro -->
            <div class="condicional-bloco mt-3" id="bloco-troco-dinheiro" style="display: none;">
              <div class="troco-pergunta-wrap">
                <span class="form-label mb-2">Precisa de troco?</span>
                <div class="troco-radios">
                  <label class="troco-radio-item">
                    <input type="radio" name="precisa_troco" value="nao" checked />
                    <span>Não preciso de troco</span>
                  </label>
                  <label class="troco-radio-item">
                    <input type="radio" name="precisa_troco" value="sim" />
                    <span>Sim, preciso de troco</span>
                  </label>
                </div>
              </div>

              <div class="form-campo mt-3" id="campo-valor-troco" style="display: none;">
                <label for="valor-troco" class="form-label">Troco para quanto?</label>
                <input type="text" id="valor-troco" name="valor_troco" class="form-input" placeholder="Ex: R$ 100,00" />
                <span class="form-erro" id="erro-valor-troco"></span>
                <div class="feedback-troco-box" id="feedback-troco-box" style="display: none; margin-top: 6px; font-size: 0.85rem; font-weight: 600;"></div>
              </div>
            </div>
          </section>

          <!-- SEÇÃO 5: Observações Gerais -->
          <section class="pedido-secao secao-obs">
            <h3 class="pedido-secao-titulo">
              <span class="secao-num">5</span>
              Observações Gerais (opcional)
            </h3>
            <textarea id="pedido-observacoes" name="pedido_observacoes" class="form-textarea" rows="2" placeholder="Ex: Tocar campainha, chamar no portão, sem talheres..."></textarea>
          </section>

          <!-- SEÇÃO 6: Resumo e Revisão do Pedido -->
          <section class="pedido-secao secao-revisao">
            <h3 class="pedido-secao-titulo">
              <span class="secao-num">✓</span>
              Resumo do Pedido
            </h3>

            <div class="revisao-card" id="revisao-card-box">
              <!-- Preenchido dinamicamente com subtotal, desconto, taxa e total -->
            </div>
          </section>

        </div>

        <!-- ============================================================ -->
        <!-- TELA PÓS-ENVIO COM INSTRUÇÕES DE PIX E CÓDIGO (TAREFA 4)      -->
        <!-- ============================================================ -->
        <div class="carrinho-tela-pos-envio" id="carrinho-tela-pos-envio" style="display: none;">
          
          <div class="pos-envio-sucesso-header">
            <div class="pos-envio-icone-check">✓</div>
            <span class="pos-envio-badge-tag">Pedido Recebido</span>
            <h3 class="pos-envio-titulo">Aguardando a confirmação da pizzaria</h3>
            <div class="pos-envio-codigo-wrap">
              <span class="codigo-label">Código do Pedido:</span>
              <span class="codigo-destaque" id="pos-envio-codigo-display">DC-0000-000</span>
            </div>
          </div>

          <!-- Bloco Específico se Pagamento for PIX -->
          <div class="pos-envio-pix-card" id="pos-envio-pix-card" style="display: none;">
            <div class="pix-card-header">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                <path d="M12 2 4 10l8 8 8-8-8-8zm0 4.24 3.76 3.76L12 13.76 8.24 10 12 6.24z"/>
              </svg>
              <h4>Pagamento via Pix</h4>
            </div>

            <p class="pix-card-instrucao">
              Copie a chave Pix abaixo e efetue o pagamento no seu banco:
            </p>

            <div class="pix-chave-box">
              <div class="pix-chave-info">
                <span class="pix-chave-tipo" id="pos-pix-tipo">Chave Celular / Pix</span>
                <span class="pix-chave-valor" id="pos-pix-chave">${config.pagamento?.pix?.chave || '65993605364'}</span>
              </div>
              <button type="button" class="btn btn--gold btn-copiar-pix" id="btn-copiar-chave-pix">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span id="btn-copiar-pix-label">Copiar Chave</span>
              </button>
            </div>

            <div class="pix-aviso-importante">
              <strong>${icone('alerta', 14)} IMPORTANTE:</strong>
              <span>${esc(config.pagamento?.pix?.avisoInstrucao || 'Faça o Pix com o valor total. Assim que conferirmos o pagamento, seu pedido é confirmado e entra em preparo.')}</span>
            </div>
          </div>

          <!-- Bloco Específico se Pagamento for Dinheiro ou Cartão -->
          <div class="pos-envio-outros-card" id="pos-envio-outros-card" style="display: none;">
            <div class="outros-card-badge">Pendente</div>
            <p id="pos-envio-outros-msg">
              A pizzaria vai conferir e confirmar seu pedido em instantes.
            </p>
          </div>

          <!-- Botões de Ação na Tela Pós-Envio -->
          <div class="pos-envio-acoes">
            <button type="button" class="btn btn--primary w-full" id="btn-acompanhar-rastreio">
              📍 Acompanhar meu pedido
            </button>

            <a href="${gerarLinkWhatsApp(config)}" target="_blank" rel="noopener noreferrer" class="btn btn--outline w-full mt-2" id="btn-duvidas-whats">
              Dúvidas? Fale com a gente no WhatsApp
            </a>

            <button type="button" class="btn btn--outline w-full mt-2" id="btn-novo-pedido">
              Fazer Outro Pedido
            </button>
          </div>


        </div>

      </div>

      <!-- Rodapé com Ações de Envio -->
      <footer class="pedido-modal-footer" id="pedido-modal-footer">
        <div class="footer-total-box">
          <span class="footer-total-label" id="footer-total-label">Total do Pedido:</span>
          <span class="footer-total-valor" id="footer-total-valor">R$ 0,00</span>
          <span class="footer-total-taxa-aviso" id="footer-taxa-aviso">+ taxa de entrega</span>
        </div>

        <button type="button" class="btn btn--primary btn--enviar-whats" id="btn-enviar-pedido-whats">
          ${icone('check', 20, 'btn-icon')}
          <span id="btn-enviar-label">Enviar Pedido</span>
        </button>
      </footer>

    </div>
  </div>
  `;
}

export function initCarrinhoModal(config) {
  const overlay = document.querySelector('#pedido-modal-overlay');
  const btnFechar = document.querySelector('#btn-fechar-modal');
  const btnAddMais = document.querySelector('#btn-add-mais');
  const btnIrCardapio = document.querySelector('#btn-ir-cardapio');
  const btnEnviar = document.querySelector('#btn-enviar-pedido-whats');
  const btnEnviarLabel = document.querySelector('#btn-enviar-label');
  
  const listaItens = document.querySelector('#pedido-itens-lista');
  const avisoVazio = document.querySelector('#carrinho-vazio-aviso');
  const conteudoAtivo = document.querySelector('#carrinho-conteudo-ativo');
  const footerModal = document.querySelector('#pedido-modal-footer');
  const subtotalDisplay = document.querySelector('#subtotal-produtos-display');
  const footerTotalValor = document.querySelector('#footer-total-valor');
  const footerTaxaAviso = document.querySelector('#footer-taxa-aviso');
  const revisaoBox = document.querySelector('#revisao-card-box');
  const sliderCompreJunto = document.querySelector('#compre-junto-slider');

  // Elementos do Bloqueio de Horário
  const avisoFechado = document.querySelector('#aviso-fechado-checkout');
  const avisoFechadoMensagem = document.querySelector('#aviso-fechado-mensagem');

  // Elementos de Endereço & Bairros
  const inputCep = document.querySelector('#entrega-cep');
  const btnCepConsultar = document.querySelector('#btn-cep-consultar');
  const cepFeedbackMsg = document.querySelector('#cep-feedback-msg');
  const inputBairroBusca = document.querySelector('#entrega-bairro-input');
  const inputBairroHidden = document.querySelector('#entrega-bairro-hidden');
  const btnBairroArrow = document.querySelector('#btn-dropdown-arrow');
  const btnTrocarBairro = document.querySelector('#btn-trocar-bairro');
  const bairroInputContainer = document.querySelector('#bairro-input-container');
  const dropdownBairros = document.querySelector('#bairros-dropdown-list');
  const campoOutroBairro = document.querySelector('#campo-outro-bairro');
  const inputOutroBairro = document.querySelector('#entrega-bairro-outro');
  const avisoTaxaDinamica = document.querySelector('#texto-taxa-dinamica');

  // Campos do formulário
  const inputNome = document.querySelector('#cliente-nome');
  const inputTelefone = document.querySelector('#cliente-telefone');
  const checkLembrarDados = document.querySelector('#lembrar-dados-check');
  const btnLimparDados = document.querySelector('#btn-limpar-dados');

  const radiosModalidade = document.querySelectorAll('input[name="modalidade_tipo"]');
  const blocoEndereco = document.querySelector('#bloco-endereco-entrega');
  const blocoRetirada = document.querySelector('#bloco-info-retirada');
  const inputRua = document.querySelector('#entrega-rua');
  const inputNumero = document.querySelector('#entrega-numero');
  const inputComplemento = document.querySelector('#entrega-complemento');
  const inputReferencia = document.querySelector('#entrega-referencia');
  const inputRetiradaHorario = document.querySelector('#retirada-horario');

  const radiosPagamento = document.querySelectorAll('input[name="forma_pagamento"]');
  const blocoAvisoPix = document.querySelector('#bloco-aviso-pix');
  const blocoTroco = document.querySelector('#bloco-troco-dinheiro');
  const radiosTroco = document.querySelectorAll('input[name="precisa_troco"]');
  const campoValorTroco = document.querySelector('#campo-valor-troco');
  const inputValorTroco = document.querySelector('#valor-troco');
  const feedbackTrocoBox = document.querySelector('#feedback-troco-box');
  const inputObs = document.querySelector('#pedido-observacoes');

  // Elementos da Tela Pós-Envio
  const telaPosEnvio = document.querySelector('#carrinho-tela-pos-envio');
  const posCodigoDisplay = document.querySelector('#pos-envio-codigo-display');
  const posPixCard = document.querySelector('#pos-envio-pix-card');
  const posPixTipo = document.querySelector('#pos-pix-tipo');
  const posPixChave = document.querySelector('#pos-pix-chave');
  const btnCopiarPix = document.querySelector('#btn-copiar-chave-pix');
  const btnCopiarPixLabel = document.querySelector('#btn-copiar-pix-label');
  const posOutrosCard = document.querySelector('#pos-envio-outros-card');
  const posOutrosMsg = document.querySelector('#pos-envio-outros-msg');
  const btnNovoPedido = document.querySelector('#btn-novo-pedido');

  // Depois do envio o carrinho é esvaziado; isso evita que a tela de confirmação seja trocada pelo "carrinho vazio"
  let telaPosEnvioAtiva = false;

  // 1. CARREGAR DADOS SALVOS NO LOCALSTORAGE (TAREFA 6)
  function carregarDadosSalvos() {
    try {
      const salvo = localStorage.getItem(STORAGE_CLIENTE_KEY);
      if (salvo) {
        const dados = JSON.parse(salvo);
        if (dados && typeof dados === 'object') {
          if (dados.nome && inputNome) inputNome.value = dados.nome;
          if (dados.telefone && inputTelefone) inputTelefone.value = dados.telefone;
          if (dados.rua && inputRua) inputRua.value = dados.rua;
          if (dados.numero && inputNumero) inputNumero.value = dados.numero;
          if (dados.complemento && inputComplemento) inputComplemento.value = dados.complemento;
          if (dados.referencia && inputReferencia) inputReferencia.value = dados.referencia;
          if (dados.cep && inputCep) inputCep.value = dados.cep;

          if (dados.bairro) {
            if (dados.bairro === 'outro' || dados.bairro.toLowerCase() === 'outro bairro' || dados.bairroOutro) {
              bloquearModoOutroBairro(dados.bairroOutro || '');
            } else {
              selecionarBairroCadastrado(dados.bairro);
            }
          }

          if (btnLimparDados) btnLimparDados.style.display = 'inline-block';
        }
      }
    } catch (e) {
      console.warn('Não foi possível ler dados salvos do cliente:', e);
    }
  }

  function salvarDadosCliente(dadosParam) {
    if (!checkLembrarDados?.checked) return;
    try {
      const dados = dadosParam || (typeof obterDadosFormulario === 'function' ? obterDadosFormulario() : null);
      const paraSalvar = {
        nome: dados?.cliente?.nome || inputNome?.value?.trim() || '',
        telefone: dados?.cliente?.telefone || inputTelefone?.value?.trim() || '',
        rua: dados?.endereco?.logradouro || inputRua?.value?.trim() || '',
        numero: dados?.endereco?.numero || inputNumero?.value?.trim() || '',
        bairro: inputBairroHidden?.value || inputBairroBusca?.value || '',
        bairroOutro: inputOutroBairro?.value?.trim() || '',
        complemento: dados?.endereco?.complemento || inputComplemento?.value?.trim() || '',
        referencia: dados?.endereco?.referencia || inputReferencia?.value?.trim() || '',
        cep: dados?.endereco?.cep || inputCep?.value?.trim() || ''
      };

      const temDado = Object.values(paraSalvar).some(v => Boolean(v));
      if (temDado) {
        localStorage.setItem(STORAGE_CLIENTE_KEY, JSON.stringify(paraSalvar));
        if (btnLimparDados) btnLimparDados.style.display = 'inline-block';
      }
    } catch (e) {
      console.warn('Não foi possível salvar dados no localStorage:', e);
    }
  }

  // Auto-salvar dados do cliente e endereço conforme o usuário preenche
  [inputNome, inputTelefone, inputCep, inputRua, inputNumero, inputComplemento, inputReferencia, inputOutroBairro].forEach(el => {
    el?.addEventListener('change', () => salvarDadosCliente());
  });

  // Botão Limpar Dados
  btnLimparDados?.addEventListener('click', () => {
    try {
      localStorage.removeItem(STORAGE_CLIENTE_KEY);
      if (inputNome) inputNome.value = '';
      if (inputTelefone) inputTelefone.value = '';
      if (inputRua) inputRua.value = '';
      if (inputNumero) inputNumero.value = '';
      if (inputComplemento) inputComplemento.value = '';
      if (inputReferencia) inputReferencia.value = '';
      if (inputCep) inputCep.value = '';
      if (inputBairroBusca) inputBairroBusca.value = '';
      if (inputBairroHidden) inputBairroHidden.value = '';
      if (inputOutroBairro) inputOutroBairro.value = '';
      if (campoOutroBairro) campoOutroBairro.style.display = 'none';
      if (cepFeedbackMsg) {
        cepFeedbackMsg.textContent = '';
        cepFeedbackMsg.className = 'form-cep-feedback';
      }

      btnLimparDados.style.display = 'none';
      atualizarRevisao();
    } catch (e) {
      console.warn('Erro ao limpar localStorage:', e);
    }
  });

  // 2. VERIFICAÇÃO DE HORÁRIO E BLOQUEIO (TAREFA 5)
  function verificarStatusFuncionamento() {
    const status = obterStatusFuncionamento(new Date(), config.horario || {});

    if (!status.podeFazerPedido) {
      if (avisoFechado) {
        avisoFechado.style.display = 'flex';
        if (avisoFechadoMensagem) {
          avisoFechadoMensagem.textContent = `Pizzaria fechada no momento: ${status.statusTexto}. Você pode consultar os valores e montar suas pizzas, mas os pedidos só podem ser finalizados quando a pizzaria estiver aberta.`;
        }
      }

      if (btnEnviar) {
        btnEnviar.disabled = true;
        btnEnviar.classList.add('btn--bloqueado');
      }
      if (btnEnviarLabel) {
        btnEnviarLabel.textContent = `Fechado · ${status.statusTexto}`;
      }
    } else {
      if (avisoFechado) avisoFechado.style.display = 'none';
      if (btnEnviar) {
        btnEnviar.disabled = false;
        btnEnviar.classList.remove('btn--bloqueado');
      }
      if (btnEnviarLabel) {
        btnEnviarLabel.textContent = 'Enviar Pedido';
      }
    }

    return status;
  }

  // 3. MÁSCARAS DE INPUT
  if (inputTelefone) {
    inputTelefone.addEventListener('input', (e) => {
      let v = e.target.value.replace(/\D/g, '');
      if (v.length > 11) v = v.slice(0, 11);
      if (v.length > 6) {
        v = `(${v.slice(0, 2)}) ${v.slice(2, 7)}-${v.slice(7)}`;
      } else if (v.length > 2) {
        v = `(${v.slice(0, 2)}) ${v.slice(2)}`;
      } else if (v.length > 0) {
        v = `(${v}`;
      }
      e.target.value = v;
      atualizarRevisao();
    });
  }

  if (inputValorTroco) {
    inputValorTroco.addEventListener('input', (e) => {
      let v = e.target.value.replace(/\D/g, '');
      if (v) {
        v = (Number(v) / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
      }
      e.target.value = v;
      atualizarRevisao();
    });
  }

  // 4. NORMALIZAÇÃO E GESTÃO INTELIGENTE DE BAIRROS (AUTOCOMPLETE & OUTRO BAIRRO)
  function normalizarTexto(str) {
    return (str || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  function encontrarBairroCorrespondente(termo) {
    const tNorm = normalizarTexto(termo);
    if (!tNorm) return null;

    let encontrado = bairrosLista.find(b => normalizarTexto(b.bairro) === tNorm);
    if (encontrado) return encontrado;

    encontrado = bairrosLista.find(b => {
      const bNorm = normalizarTexto(b.bairro);
      return bNorm.includes(tNorm) || tNorm.includes(bNorm);
    });
    return encontrado || null;
  }

  function bloquearModoOutroBairro(nomeBairro = '') {
    if (inputBairroBusca) {
      inputBairroBusca.value = 'Outro Bairro';
      inputBairroBusca.readOnly = true;
      inputBairroBusca.classList.add('bairro-input-bloqueado');
      inputBairroBusca.classList.remove('input-invalido');
    }
    if (inputBairroHidden) {
      inputBairroHidden.value = 'outro';
    }
    if (bairroInputContainer) {
      bairroInputContainer.classList.add('is-bloqueado');
    }
    if (btnTrocarBairro) {
      btnTrocarBairro.style.display = 'inline-flex';
    }
    if (campoOutroBairro) {
      campoOutroBairro.style.display = 'block';
    }
    if (inputOutroBairro) {
      inputOutroBairro.disabled = false;
      const bNomeLimpo = (nomeBairro || '').trim();
      if (bNomeLimpo && bNomeLimpo.toLowerCase() !== 'outro' && bNomeLimpo.toLowerCase() !== 'outro bairro') {
        inputOutroBairro.value = bNomeLimpo;
      }
    }
    const elErro = document.querySelector('#erro-entrega-bairro');
    if (elErro) elErro.textContent = '';
    fecharDropdownBairros();
    atualizarRevisao();
    salvarDadosCliente();
  }

  function desbloquearModoBairro() {
    if (inputBairroBusca) {
      inputBairroBusca.readOnly = false;
      inputBairroBusca.classList.remove('bairro-input-bloqueado');
      inputBairroBusca.value = '';
    }
    if (inputBairroHidden) {
      inputBairroHidden.value = '';
    }
    if (bairroInputContainer) {
      bairroInputContainer.classList.remove('is-bloqueado');
    }
    if (btnTrocarBairro) {
      btnTrocarBairro.style.display = 'none';
    }
    if (campoOutroBairro) {
      campoOutroBairro.style.display = 'none';
    }
    if (inputOutroBairro) {
      inputOutroBairro.value = '';
      inputOutroBairro.classList.remove('input-invalido');
    }
    abrirDropdownBairros('');
    inputBairroBusca?.focus();
    atualizarRevisao();
  }

  function selecionarBairroCadastrado(bNome) {
    if (inputBairroBusca) {
      inputBairroBusca.readOnly = false;
      inputBairroBusca.classList.remove('bairro-input-bloqueado');
      inputBairroBusca.value = bNome;
      inputBairroBusca.classList.remove('input-invalido');
    }
    if (inputBairroHidden) {
      inputBairroHidden.value = bNome;
    }
    if (bairroInputContainer) {
      bairroInputContainer.classList.remove('is-bloqueado');
    }
    if (btnTrocarBairro) {
      btnTrocarBairro.style.display = 'none';
    }
    if (campoOutroBairro) {
      campoOutroBairro.style.display = 'none';
    }
    if (inputOutroBairro) {
      inputOutroBairro.value = '';
      inputOutroBairro.classList.remove('input-invalido');
    }
    const elErro = document.querySelector('#erro-entrega-bairro');
    if (elErro) elErro.textContent = '';
    fecharDropdownBairros();
    atualizarRevisao();
    salvarDadosCliente();
  }

  function renderizarOpcoesBairro(filtro = '') {
    if (!dropdownBairros) return;
    const filtroNorm = normalizarTexto(filtro);

    let filtrados = bairrosLista;
    if (filtroNorm) {
      filtrados = bairrosLista.filter(b => {
        const bNorm = normalizarTexto(b.bairro);
        const cNorm = normalizarTexto(b.cidade);
        return bNorm.includes(filtroNorm) || cNorm.includes(filtroNorm);
      });
    }

    let html = '';

    if (filtrados.length === 0) {
      html += `
        <div class="bairro-sem-resultado">
          Nenhum bairro cadastrado encontrado para "<strong>${esc(filtro)}</strong>".
        </div>
        <div class="bairro-dropdown-item bairro-item-outro" data-bairro="outro" data-custom="${esc(filtro)}">
          <div class="bairro-item-info">
            <span class="bairro-item-nome">Usar "${esc(filtro)}" como Outro Bairro</span>
            <span class="bairro-item-cidade">Bairro não listado</span>
          </div>
          <span class="bairro-item-taxa" style="font-size: 0.72rem;">A confirmar</span>
        </div>
      `;
    } else {
      html += filtrados.map(b => `
        <div class="bairro-dropdown-item" data-bairro="${esc(b.bairro)}" data-taxa="${b.taxa}">
          <div class="bairro-item-info">
            <span class="bairro-item-nome">${esc(b.bairro)}</span>
            <span class="bairro-item-cidade">${esc(b.cidade)}</span>
          </div>
          <span class="bairro-item-taxa">${formatarPreco(b.taxa)}</span>
        </div>
      `).join('');

      html += `
        <div class="bairro-dropdown-item bairro-item-outro" data-bairro="outro" data-custom="">
          <div class="bairro-item-info">
            <span class="bairro-item-nome">Outro bairro não listado...</span>
            <span class="bairro-item-cidade">Cuiabá / Várzea Grande</span>
          </div>
          <span class="bairro-item-taxa" style="font-size: 0.72rem;">A confirmar</span>
        </div>
      `;
    }

    dropdownBairros.innerHTML = html;

    dropdownBairros.querySelectorAll('.bairro-dropdown-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        const bNome = item.dataset.bairro;
        if (bNome === 'outro') {
          const custom = item.dataset.custom || (inputBairroBusca?.value?.trim() !== 'Outro Bairro' ? inputBairroBusca?.value?.trim() : '');
          bloquearModoOutroBairro(custom);
          inputOutroBairro?.focus();
        } else {
          selecionarBairroCadastrado(bNome);
        }
      });
    });
  }

  function abrirDropdownBairros(filtro = '') {
    renderizarOpcoesBairro(filtro);
    if (dropdownBairros) dropdownBairros.style.display = 'block';
    btnBairroArrow?.classList.add('is-open');
  }

  function fecharDropdownBairros() {
    if (dropdownBairros) dropdownBairros.style.display = 'none';
    btnBairroArrow?.classList.remove('is-open');
  }

  // Ouvintes da Busca de Bairro por Digitação
  if (inputBairroBusca) {
    inputBairroBusca.addEventListener('input', (e) => {
      if (inputBairroBusca.readOnly) return;
      const digitado = e.target.value;
      if (inputBairroHidden) inputBairroHidden.value = '';
      abrirDropdownBairros(digitado);

      // Se coincidir exatamente com algum bairro cadastrado
      const encontrado = encontrarBairroCorrespondente(digitado);
      if (encontrado && normalizarTexto(encontrado.bairro) === normalizarTexto(digitado)) {
        if (inputBairroHidden) inputBairroHidden.value = encontrado.bairro;
      }
      atualizarRevisao();
    });

    inputBairroBusca.addEventListener('focus', () => {
      if (inputBairroBusca.readOnly) return;
      abrirDropdownBairros(inputBairroBusca.value);
    });

    inputBairroBusca.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const itemOutro = dropdownBairros?.querySelector('.bairro-dropdown-item[data-custom]');
        const primeiroItem = dropdownBairros?.querySelector('.bairro-dropdown-item');
        if (itemOutro) {
          itemOutro.click();
        } else if (primeiroItem) {
          primeiroItem.click();
        } else {
          const digitado = inputBairroBusca.value.trim();
          if (digitado && digitado !== 'Outro Bairro') {
            bloquearModoOutroBairro(digitado);
            inputOutroBairro?.focus();
          } else {
            fecharDropdownBairros();
          }
        }
      } else if (e.key === 'Escape') {
        fecharDropdownBairros();
      }
    });

    inputBairroBusca.addEventListener('blur', () => {
      setTimeout(() => {
        if (inputBairroBusca.readOnly) return;
        const digitado = inputBairroBusca.value.trim();
        if (!digitado || digitado === 'Outro Bairro') return;

        if (!inputBairroHidden?.value) {
          const correspondente = encontrarBairroCorrespondente(digitado);
          if (correspondente) {
            selecionarBairroCadastrado(correspondente.bairro);
          } else {
            bloquearModoOutroBairro(digitado);
          }
        }
      }, 250);
    });
  }

  btnTrocarBairro?.addEventListener('click', (e) => {
    e.stopPropagation();
    desbloquearModoBairro();
  });

  btnBairroArrow?.addEventListener('click', (e) => {
    e.stopPropagation();
    if (inputBairroBusca?.readOnly) {
      desbloquearModoBairro();
      return;
    }
    if (dropdownBairros?.style.display === 'block') {
      fecharDropdownBairros();
    } else {
      abrirDropdownBairros(inputBairroBusca?.value || '');
    }
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('#bairro-search-wrapper')) {
      fecharDropdownBairros();
    }
  });

  inputOutroBairro?.addEventListener('input', atualizarRevisao);

  // 5. CONSULTA AUTOMÁTICA DE CEP (VIACEP)
  async function consultarCep(cepValor) {
    const cepLimpo = (cepValor || '').replace(/\D/g, '');
    if (cepLimpo.length !== 8) {
      if (cepFeedbackMsg) {
        cepFeedbackMsg.className = 'form-cep-feedback erro';
        cepFeedbackMsg.textContent = 'Informe um CEP válido com 8 números.';
      }
      return;
    }

    if (btnCepConsultar) {
      btnCepConsultar.disabled = true;
      const statusTxt = btnCepConsultar.querySelector('#cep-status-texto');
      if (statusTxt) statusTxt.textContent = 'Buscando...';
    }
    if (cepFeedbackMsg) {
      cepFeedbackMsg.className = 'form-cep-feedback buscando';
      cepFeedbackMsg.textContent = 'Consultando CEP no ViaCEP...';
    }

    try {
      const resp = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`);
      const dados = await resp.json();

      if (dados.erro) {
        if (cepFeedbackMsg) {
          cepFeedbackMsg.className = 'form-cep-feedback erro';
          cepFeedbackMsg.textContent = 'CEP não encontrado. Preencha os campos abaixo manualmente.';
        }
        return;
      }

      // Preenche Rua / Avenida
      if (inputRua && dados.logradouro) {
        inputRua.value = dados.logradouro;
        inputRua.classList.remove('input-invalido');
      }

      // Preenche Cidade
      const inputCidade = document.querySelector('#entrega-cidade');
      if (inputCidade && dados.localidade) {
        inputCidade.value = `${dados.localidade} — ${dados.uf || 'MT'}`;
      }

      // Preenche Bairro e sincroniza com a taxa
      if (dados.bairro) {
        const correspondente = encontrarBairroCorrespondente(dados.bairro);
        if (correspondente) {
          selecionarBairroCadastrado(correspondente.bairro);
        } else {
          // Bairro NÃO listado: bloqueia com "Outro Bairro" e habilita "Nome do seu bairro"
          bloquearModoOutroBairro(dados.bairro);
        }
      }

      if (cepFeedbackMsg) {
        cepFeedbackMsg.className = 'form-cep-feedback sucesso';
        cepFeedbackMsg.textContent = `✓ Endereço carregado: ${dados.logradouro ? dados.logradouro + ', ' : ''}${dados.bairro} (${dados.localidade})`;
      }

      // Direciona o foco para o número
      if (inputNumero && !inputNumero.value) {
        inputNumero.focus();
      }

      atualizarRevisao();
      salvarDadosCliente();
    } catch (err) {
      console.warn('Erro ao consultar ViaCEP:', err);
      if (cepFeedbackMsg) {
        cepFeedbackMsg.className = 'form-cep-feedback erro';
        cepFeedbackMsg.textContent = 'Não foi possível consultar o CEP no momento. Preencha manualmente.';
      }
    } finally {
      if (btnCepConsultar) {
        btnCepConsultar.disabled = false;
        const statusTxt = btnCepConsultar.querySelector('#cep-status-texto');
        if (statusTxt) statusTxt.textContent = 'Buscar';
      }
    }
  }

  // Ouvintes do CEP
  if (inputCep) {
    inputCep.addEventListener('input', (e) => {
      let v = e.target.value.replace(/\D/g, '');
      if (v.length > 8) v = v.slice(0, 8);
      if (v.length > 5) {
        v = `${v.slice(0, 5)}-${v.slice(5)}`;
      }
      e.target.value = v;

      const limpo = v.replace(/\D/g, '');
      if (limpo.length === 8) {
        consultarCep(limpo);
      } else if (cepFeedbackMsg && limpo.length === 0) {
        cepFeedbackMsg.textContent = '';
        cepFeedbackMsg.className = 'form-cep-feedback';
      }
      atualizarRevisao();
    });
  }

  btnCepConsultar?.addEventListener('click', () => {
    consultarCep(inputCep?.value || '');
  });

  // Ouvintes nos demais inputs para reatividade
  [inputNome, inputRua, inputNumero, inputComplemento, inputReferencia, inputRetiradaHorario, inputObs].forEach(input => {
    input?.addEventListener('input', atualizarRevisao);
  });

  // Modalidade (Entrega vs Retirada)
  radiosModalidade.forEach(radio => {
    radio.addEventListener('change', () => {
      const cardEntrega = document.querySelector('#modalidade-card-entrega');
      const cardRetirada = document.querySelector('#modalidade-card-retirada');
      
      if (radio.value === 'entrega') {
        cardEntrega?.classList.add('active');
        cardRetirada?.classList.remove('active');
        if (blocoEndereco) blocoEndereco.style.display = 'block';
        if (blocoRetirada) blocoRetirada.style.display = 'none';
      } else {
        cardRetirada?.classList.add('active');
        cardEntrega?.classList.remove('active');
        if (blocoEndereco) blocoEndereco.style.display = 'none';
        if (blocoRetirada) blocoRetirada.style.display = 'block';
      }
      atualizarRevisao();
    });
  });

  // Forma de Pagamento
  radiosPagamento.forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.pagamento-opcao').forEach(lbl => lbl.classList.remove('active'));
      radio.closest('.pagamento-opcao')?.classList.add('active');

      if (radio.value === 'pix') {
        if (blocoAvisoPix) blocoAvisoPix.style.display = 'block';
        if (blocoTroco) blocoTroco.style.display = 'none';
      } else if (radio.value === 'dinheiro') {
        if (blocoAvisoPix) blocoAvisoPix.style.display = 'none';
        if (blocoTroco) blocoTroco.style.display = 'block';
      } else {
        if (blocoAvisoPix) blocoAvisoPix.style.display = 'none';
        if (blocoTroco) blocoTroco.style.display = 'none';
      }
      atualizarRevisao();
    });
  });

  // Troco Radio
  radiosTroco.forEach(radio => {
    radio.addEventListener('change', () => {
      if (radio.value === 'sim') {
        if (campoValorTroco) campoValorTroco.style.display = 'block';
      } else {
        if (campoValorTroco) campoValorTroco.style.display = 'none';
      }
      atualizarRevisao();
    });
  });

  // 5. RENDERIZAÇÃO DOS ITENS DO CARRINHO
  function renderizarItensModal() {
    if (telaPosEnvioAtiva) return;
    const itens = carrinho.obterItens();
    const subtotal = carrinho.obterSubtotal();

    if (itens.length === 0) {
      if (avisoVazio) avisoVazio.style.display = 'block';
      if (conteudoAtivo) conteudoAtivo.style.display = 'none';
      if (footerModal) footerModal.style.display = 'none';
      if (telaPosEnvio) telaPosEnvio.style.display = 'none';
      return;
    }

    if (avisoVazio) avisoVazio.style.display = 'none';
    if (conteudoAtivo) conteudoAtivo.style.display = 'block';
    if (footerModal) footerModal.style.display = 'flex';
    if (telaPosEnvio) telaPosEnvio.style.display = 'none';

    verificarStatusFuncionamento();

    if (listaItens) {
      listaItens.innerHTML = itens.map(item => {
        const precoUnit = typeof item.precoUnitario === 'number' ? item.precoUnitario : (item.preco || 0);
        const itemSubtotal = precoUnit * (item.quantidade || 1);

        if (item.tipo === 'pizza') {
          const tituloPizza = formatarTituloPizza(item, config);
          const listaSaboresHtml = (item.sabores || []).map(s => `
            <span class="pizza-sabor-pill">• ${esc(s.nome)}</span>
          `).join('');

          let bordaHtml = '';
          if (item.borda && item.borda.id !== 'sem-borda') {
            const precoBordaTxt = (typeof item.borda.preco === 'number' && item.borda.preco > 0)
              ? ` (+${formatarPreco(item.borda.preco)})`
              : (item.borda.precoTexto ? ` (${item.borda.precoTexto})` : '');
            bordaHtml = `<div class="item-borda-tag"><strong>Borda:</strong> ${esc(item.borda.nome)}${precoBordaTxt}</div>`;
          }

          const precoUnitTexto = (typeof precoUnit === 'number' && precoUnit > 0) ? `${formatarPreco(precoUnit)} cada` : 'Sob consulta';
          const subtotalTexto = (typeof itemSubtotal === 'number' && itemSubtotal > 0) ? formatarPreco(itemSubtotal) : 'A confirmar';

          return `
          <div class="item-linha pizza-item-card" data-item-id="${item.id}">
            <img src="${item.foto}" alt="${esc(tituloPizza)}" class="item-thumb" />
            <div class="item-detalhes">
              <h4 class="item-nome">${esc(tituloPizza)}</h4>
              <div class="pizza-sabores-wrap">
                ${listaSaboresHtml}
              </div>
              ${bordaHtml}
              <div class="item-meta-row">
                <span class="item-unitario">${precoUnitTexto}</span>
                <button type="button" class="btn-editar-pizza-item" data-action="edit">
                  ${icone('editar', 13)} Editar Sabores / Borda
                </button>
              </div>
            </div>
            <div class="item-qty-controles">
              <button type="button" class="btn-qty btn-qty-minus" data-action="minus" aria-label="Diminuir quantidade">−</button>
              <span class="item-qty-num">${item.quantidade}</span>
              <button type="button" class="btn-qty btn-qty-plus" data-action="plus" aria-label="Aumentar quantidade">+</button>
            </div>
            <div class="item-total-preco">
              ${subtotalTexto}
            </div>
            <button type="button" class="btn-item-remover" data-action="remove" aria-label="Remover item">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
          `;
        } else {
          const precoUnitTexto = (typeof precoUnit === 'number' && precoUnit > 0) ? `${formatarPreco(precoUnit)} cada` : 'Sob consulta';
          const subtotalTexto = (typeof itemSubtotal === 'number' && itemSubtotal > 0) ? formatarPreco(itemSubtotal) : 'A confirmar';

          return `
          <div class="item-linha" data-item-id="${item.id}">
            <img src="${item.foto}" alt="${esc(item.nome)}" class="item-thumb" />
            <div class="item-detalhes">
              <h4 class="item-nome">${esc(item.nome)}</h4>
              <span class="item-unitario">${precoUnitTexto}</span>
            </div>
            <div class="item-qty-controles">
              <button type="button" class="btn-qty btn-qty-minus" data-action="minus" aria-label="Diminuir quantidade">−</button>
              <span class="item-qty-num">${item.quantidade}</span>
              <button type="button" class="btn-qty btn-qty-plus" data-action="plus" aria-label="Aumentar quantidade">+</button>
            </div>
            <div class="item-total-preco">
              ${subtotalTexto}
            </div>
            <button type="button" class="btn-item-remover" data-action="remove" aria-label="Remover item">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
          `;
        }
      }).join('');

      // Eventos dos botões de cada item
      listaItens.querySelectorAll('.item-linha').forEach(linha => {
        const itemId = linha.dataset.itemId;
        const itemObj = itens.find(i => i.id === itemId);

        linha.querySelector('[data-action="minus"]')?.addEventListener('click', () => {
          carrinho.alterarQuantidadeDelta(itemId, -1);
        });
        linha.querySelector('[data-action="plus"]')?.addEventListener('click', () => {
          carrinho.alterarQuantidadeDelta(itemId, 1);
        });
        linha.querySelector('[data-action="remove"]')?.addEventListener('click', () => {
          carrinho.removerItem(itemId);
        });
        linha.querySelector('[data-action="edit"]')?.addEventListener('click', () => {
          if (itemObj && itemObj.tipo === 'pizza') {
            fechar();
            carrinho.abrirModalPizza(null, itemObj);
          }
        });
      });
    }

    if (subtotalDisplay) subtotalDisplay.textContent = formatarPreco(subtotal);
    renderizarCompreJunto();
    atualizarRevisao();
  }

  // 5.1 RENDERIZAÇÃO DA SEÇÃO COMPRE JUNTO (UPSELL RÁPIDO)
  function renderizarCompreJunto() {
    if (!sliderCompreJunto) return;
    const itensCarrinho = carrinho.obterItens();

    sliderCompreJunto.innerHTML = ITENS_COMPRE_JUNTO.map(item => {
      const itemNoCarrinho = itensCarrinho.find(i => i.idProduto === item.id || (i.tipo === 'simples' && i.nome === item.nome));
      const qtdNoCarrinho = itemNoCarrinho ? itemNoCarrinho.quantidade : 0;
      const jaAdicionado = qtdNoCarrinho > 0;

      const btnLabel = jaAdicionado ? `+1 Mais (${qtdNoCarrinho})` : '+ Adicionar';
      const btnClass = jaAdicionado ? 'btn-compre-junto-add is-added' : 'btn-compre-junto-add';

      return `
      <div class="compre-junto-card ${jaAdicionado ? 'ja-adicionado' : ''}" data-produto-id="${item.id}">
        <div class="compre-junto-card-top">
          <span class="compre-junto-badge-cat">${esc(item.categoriaLabel)}</span>
          <span class="compre-junto-icon">${icone(item.icone, 16)}</span>
        </div>
        <h5 class="compre-junto-card-nome">${esc(item.nome)}</h5>
        <p class="compre-junto-card-sub">${esc(item.subtitulo)}</p>
        <div class="compre-junto-card-footer">
          <span class="compre-junto-preco">${formatarPreco(item.preco)}</span>
          <button type="button" class="${btnClass}" data-action="quick-add" data-id="${item.id}" aria-label="Adicionar ${esc(item.nome)} ao pedido">
            ${jaAdicionado ? icone('check', 13) : icone('mais', 13)}
            <span>${btnLabel}</span>
          </button>
        </div>
      </div>
      `;
    }).join('');

    sliderCompreJunto.querySelectorAll('[data-action="quick-add"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idProd = btn.dataset.id;
        const produto = ITENS_COMPRE_JUNTO.find(p => p.id === idProd);
        if (produto) {
          carrinho.adicionarItemSimples(produto, 1);
        }
      });
    });
  }

  // 6. EXTRAÇÃO DOS DADOS DO FORMULÁRIO COM TAXA E PROMOÇÃO
  function obterDadosFormulario() {
    const modalidade = document.querySelector('input[name="modalidade_tipo"]:checked')?.value || 'entrega';
    const formaPag = document.querySelector('input[name="forma_pagamento"]:checked')?.value || 'pix';
    const precisaTroco = document.querySelector('input[name="precisa_troco"]:checked')?.value || 'nao';

    const bairroInputVal = inputBairroBusca?.value?.trim() || '';
    const bairroHiddenVal = inputBairroHidden?.value?.trim() || '';
    let bairroFinal = bairroHiddenVal || bairroInputVal;
    if (bairroHiddenVal === 'outro' || !bairroFinal) {
      bairroFinal = inputOutroBairro?.value?.trim() || bairroInputVal || 'Outro bairro (a confirmar)';
    }

    const entregaInfo = calcularTaxaEntrega(modalidade, bairroFinal, bairrosLista);
    if ((bairroHiddenVal === 'outro' || entregaInfo.statusTaxa === 'a_confirmar') && inputOutroBairro?.value?.trim()) {
      entregaInfo.bairro = inputOutroBairro.value.trim();
    }

    // Promoção
    const subtotal = carrinho.obterSubtotal();
    const promo = obterPromocaoAtiva(config.promocao);
    const desconto = promo.ativa ? promo.calcularDesconto(subtotal) : 0;
    const promocaoInfo = {
      ativa: promo.ativa,
      titulo: promo.titulo,
      cupom: promo.cupom,
      desconto,
      descontoPercentual: promo.descontoPercentual
    };

    return {
      itens: carrinho.obterItens(),
      cliente: {
        nome: inputNome?.value?.trim() || '',
        telefone: inputTelefone?.value?.trim() || ''
      },
      modalidade,
      entregaInfo,
      promocaoInfo,
      endereco: {
        logradouro: inputRua?.value?.trim() || '',
        numero: inputNumero?.value?.trim() || '',
        bairro: bairroFinal,
        complemento: inputComplemento?.value?.trim() || '',
        referencia: inputReferencia?.value?.trim() || '',
        cidade: 'Cuiabá',
        estado: 'MT',
        cep: inputCep?.value?.trim() || ''
      },
      retirada: {
        unidade: 'Avenida Brasil, 2055, Cidade Alta, Cuiabá - MT',
        tempoEstimado: config.operacional?.tempoRetirada || config.pagamento?.tempoMedioRetirada || '20 a 35 min',
        horarioPretendido: inputRetiradaHorario?.value?.trim() || ''
      },
      pagamento: {
        forma: formaPag,
        precisaTroco,
        trocoPara: precisaTroco === 'sim' ? inputValorTroco?.value?.trim() : ''
      },
      observacoes: inputObs?.value?.trim() || ''
    };
  }

  // 7. ATUALIZAÇÃO DO RESUMO E RODAPÉ EM TEMPO REAL
  function atualizarRevisao() {
    if (!revisaoBox) return;
    const dados = obterDadosFormulario();
    const subtotal = carrinho.obterSubtotal();
    const desconto = dados.promocaoInfo.desconto || 0;
    const subtotalComDesconto = Math.max(0, subtotal - desconto);
    const pedidoMinimo = config.regrasComerciais?.pedidoMinimo || config.pagamento?.pedidoMinimo || 23.00;
    const tempoRetiradaPadrao = config.operacional?.tempoRetirada || config.pagamento?.tempoMedioRetirada || '20 a 35 min';

    // Texto dinâmico de taxa
    if (avisoTaxaDinamica) {
      if (dados.modalidade === 'retirada') {
        avisoTaxaDinamica.innerHTML = `<strong>Retirada no balcão:</strong> sem taxa de entrega (R$ 0,00) · <strong>Tempo médio:</strong> ${tempoRetiradaPadrao}.`;
      } else {
        if (dados.entregaInfo.statusTaxa === 'definida') {
          avisoTaxaDinamica.innerHTML = `<strong>Taxa para ${esc(dados.entregaInfo.bairro)}:</strong> ${formatarPreco(dados.entregaInfo.taxa)}`;
        } else if (dados.entregaInfo.statusTaxa === 'a_confirmar' && (inputBairroBusca?.value?.trim() || inputOutroBairro?.value?.trim())) {
          const bNomeAviso = inputOutroBairro?.value?.trim() || inputBairroBusca?.value?.trim() || 'Outro bairro';
          avisoTaxaDinamica.innerHTML = `<strong>${esc(bNomeAviso)}:</strong> taxa confirmada pela pizzaria junto com o pedido.`;
        } else {
          avisoTaxaDinamica.innerHTML = '<strong>Taxa de entrega:</strong> informe o CEP ou digite seu bairro acima para calcular.';
        }
      }
    }

    let enderecoOuRetiradaHtml = '';
    let taxaLinhaHtml = '';

    if (dados.modalidade === 'entrega') {
      const enderecoTexto = [
        dados.endereco.logradouro ? `${dados.endereco.logradouro}, ${dados.endereco.numero || 'S/N'}` : null,
        dados.endereco.bairro ? `Bairro: ${dados.endereco.bairro}` : null,
        'Cuiabá / VG'
      ].filter(Boolean).join(' · ');

      enderecoOuRetiradaHtml = `
        <div class="rev-linha">
          <span class="rev-label">Entrega em:</span>
          <span class="rev-val">${esc(enderecoTexto || 'Informe o endereço acima')}</span>
        </div>
      `;

      if (dados.entregaInfo.statusTaxa === 'definida') {
        taxaLinhaHtml = `
          <div class="rev-linha">
            <span class="rev-label">Taxa de entrega (${esc(dados.entregaInfo.bairro)}):</span>
            <span class="rev-val text-gold">${formatarPreco(dados.entregaInfo.taxa)}</span>
          </div>
        `;
      } else {
        taxaLinhaHtml = `
          <div class="rev-linha">
            <span class="rev-label">Taxa de entrega:</span>
            <span class="rev-val text-gold">A confirmar com a atendente</span>
          </div>
        `;
      }
    } else {
      enderecoOuRetiradaHtml = `
        <div class="rev-linha">
          <span class="rev-label">Modalidade:</span>
          <span class="rev-val">Retirada no balcão (Cidade Alta)</span>
        </div>
        <div class="rev-linha">
          <span class="rev-label">Tempo médio de preparo:</span>
          <span class="rev-val text-gold">${tempoRetiradaPadrao}</span>
        </div>
      `;
      taxaLinhaHtml = `
        <div class="rev-linha">
          <span class="rev-label">Taxa de entrega:</span>
          <span class="rev-val text-gold">R$ 0,00 (Grátis)</span>
        </div>
      `;
    }

    // Linha de promoção / desconto
    let descontoHtml = '';
    if (desconto > 0) {
      descontoHtml = `
        <div class="rev-linha desconto-linha">
          <span class="rev-label text-gold">Desconto (${dados.promocaoInfo.descontoPercentual}%):</span>
          <span class="rev-val text-gold">- ${formatarPreco(desconto)}</span>
        </div>
      `;
    }

    // Linha de alerta de pedido mínimo
    let avisoPedidoMinimoHtml = '';
    if (subtotal > 0 && subtotal < pedidoMinimo) {
      const diferenca = pedidoMinimo - subtotal;
      avisoPedidoMinimoHtml = `
        <div class="rev-linha aviso-minimo-linha">
          <span class="rev-label text-danger">${icone('alerta', 14)} Pedido Mínimo: ${formatarPreco(pedidoMinimo)}</span>
          <span class="rev-val text-danger">Adicione mais ${formatarPreco(diferenca)}</span>
        </div>
      `;
    }

    // Linha de aviso de itens com valor sob consulta
    const temItensSobConsulta = dados.itens.some(item => 
      (typeof item.precoUnitario !== 'number' && typeof item.preco !== 'number') || 
      (!item.preco && item.tipo !== 'pizza')
    );
    let avisoItensSobConsultaHtml = '';
    if (temItensSobConsulta) {
      avisoItensSobConsultaHtml = `
        <div class="rev-linha aviso-sob-consulta-linha">
          <span class="rev-label text-gold">${icone('info', 14)} Preços sob consulta:</span>
          <span class="rev-val text-gold">Valores a confirmar com atendente</span>
        </div>
      `;
    }

    // Cálculo do total final
    let totalDisplayTexto = '';
    let footerAvisoTexto = '';

    if (dados.modalidade === 'retirada') {
      totalDisplayTexto = formatarPreco(subtotalComDesconto);
      footerAvisoTexto = temItensSobConsulta ? `Retirada (${tempoRetiradaPadrao}) · + itens a confirmar` : `Retirada no balcão · Pronto em ${tempoRetiradaPadrao}`;
    } else if (dados.entregaInfo.statusTaxa === 'definida') {
      const totalComTaxa = subtotalComDesconto + dados.entregaInfo.taxa;
      totalDisplayTexto = formatarPreco(totalComTaxa);
      footerAvisoTexto = temItensSobConsulta 
        ? `Inclui entrega (${formatarPreco(dados.entregaInfo.taxa)}) · + itens a confirmar`
        : `Inclui entrega (${formatarPreco(dados.entregaInfo.taxa)})`;
    } else {
      totalDisplayTexto = `${formatarPreco(subtotalComDesconto)}`;
      footerAvisoTexto = temItensSobConsulta 
        ? '+ taxa e itens a confirmar'
        : '+ taxa de entrega a confirmar';
    }

    if (footerTotalValor) footerTotalValor.textContent = totalDisplayTexto;
    if (footerTaxaAviso) footerTaxaAviso.textContent = footerAvisoTexto;

    let dinheiroTexto = 'Dinheiro';
    const totalNumericoRevisao = subtotalComDesconto + (dados.modalidade === 'entrega' && dados.entregaInfo.statusTaxa === 'definida' ? dados.entregaInfo.taxa : 0);

    if (dados.pagamento.forma === 'dinheiro') {
      if (dados.pagamento.precisaTroco === 'sim') {
        const vPago = extrairNumeroMoeda(dados.pagamento.trocoPara);
        if (vPago > totalNumericoRevisao) {
          const trocoCalc = vPago - totalNumericoRevisao;
          dinheiroTexto = `Dinheiro (Troco para ${formatarPreco(vPago)} · Levar ${formatarPreco(trocoCalc)})`;
          if (feedbackTrocoBox) {
            feedbackTrocoBox.style.display = 'block';
            feedbackTrocoBox.style.color = '#52B788';
            feedbackTrocoBox.innerHTML = `👉 Troco a levar pelo motoboy: <strong>${formatarPreco(trocoCalc)}</strong> (Troco para ${formatarPreco(vPago)})`;
          }
        } else if (vPago === totalNumericoRevisao && vPago > 0) {
          dinheiroTexto = `Dinheiro (Valor exato ${formatarPreco(vPago)} · Sem troco)`;
          if (feedbackTrocoBox) {
            feedbackTrocoBox.style.display = 'block';
            feedbackTrocoBox.style.color = '#F0D59A';
            feedbackTrocoBox.innerHTML = `👉 Pagamento no valor exato do pedido (Não precisa de troco).`;
          }
        } else if (vPago > 0) {
          dinheiroTexto = `Dinheiro (Troco para ${dados.pagamento.trocoPara})`;
          if (feedbackTrocoBox) {
            feedbackTrocoBox.style.display = 'block';
            feedbackTrocoBox.style.color = '#E63946';
            feedbackTrocoBox.innerHTML = `⚠️ O valor informado (${formatarPreco(vPago)}) deve ser maior que o total do pedido (${formatarPreco(totalNumericoRevisao)}).`;
          }
        } else {
          dinheiroTexto = 'Dinheiro (Com troco a informar)';
          if (feedbackTrocoBox) {
            feedbackTrocoBox.style.display = 'none';
          }
        }
      } else {
        dinheiroTexto = 'Dinheiro (Sem troco · Valor exato)';
        if (feedbackTrocoBox) {
          feedbackTrocoBox.style.display = 'none';
        }
      }
    } else {
      if (feedbackTrocoBox) {
        feedbackTrocoBox.style.display = 'none';
      }
    }

    const nomesPag = {
      pix: 'Pix',
      dinheiro: dinheiroTexto,
      cartao_credito: 'Cartão de Crédito',
      cartao_debito: 'Cartão de Débito'
    };

    revisaoBox.innerHTML = `
      <div class="rev-linha">
        <span class="rev-label">Cliente:</span>
        <span class="rev-val">${esc(dados.cliente.nome || 'Pendente')} · ${esc(dados.cliente.telefone || 'Pendente')}</span>
      </div>
      ${enderecoOuRetiradaHtml}
      <div class="rev-linha">
        <span class="rev-label">Pagamento:</span>
        <span class="rev-val">${nomesPag[dados.pagamento.forma] || 'Pix'}</span>
      </div>
      <div class="rev-linha">
        <span class="rev-label">Subtotal dos produtos:</span>
        <span class="rev-val">${formatarPreco(subtotal)}</span>
      </div>
      ${avisoPedidoMinimoHtml}
      ${avisoItensSobConsultaHtml}
      ${descontoHtml}
      ${taxaLinhaHtml}
      <div class="rev-linha total-linha">
        <span class="rev-label">Total do Pedido:</span>
        <span class="rev-val-destaque">${totalDisplayTexto}</span>
      </div>
    `;
  }

  // 8. VALIDAÇÃO DO FORMULÁRIO
  function limparErros() {
    document.querySelectorAll('.form-erro').forEach(el => el.textContent = '');
    document.querySelectorAll('.form-input').forEach(el => el.classList.remove('input-invalido'));
  }

  function validarFormulario() {
    limparErros();
    let valido = true;
    let primeiroElementoInvalido = null;

    const pedidoMinimo = config.regrasComerciais?.pedidoMinimo || config.pagamento?.pedidoMinimo || 23.00;
    const subtotalAtual = carrinho.obterSubtotal();
    if (subtotalAtual > 0 && subtotalAtual < pedidoMinimo) {
      alert(`O valor mínimo para pedidos na Don Corleone é de ${formatarPreco(pedidoMinimo)}. Por favor, adicione mais itens ao seu carrinho.`);
      return false;
    }

    const marcarErro = (input, idErro, mensagem) => {
      valido = false;
      if (input) input.classList.add('input-invalido');
      const elErro = document.querySelector(`#${idErro}`);
      if (elErro) elErro.textContent = mensagem;
      if (!primeiroElementoInvalido && input) primeiroElementoInvalido = input;
    };

    // Validar Nome
    if (!inputNome?.value?.trim()) {
      marcarErro(inputNome, 'erro-cliente-nome', 'Por favor, informe seu nome completo.');
    }

    // Validar Telefone (mínimo 10 dígitos)
    const telDigits = inputTelefone?.value?.replace(/\D/g, '') || '';
    if (telDigits.length < 10) {
      marcarErro(inputTelefone, 'erro-cliente-telefone', 'Informe um telefone válido com DDD (ex: 65 99999-9999).');
    }

    // Validar Endereço se modalidade for Entrega
    const modalidade = document.querySelector('input[name="modalidade_tipo"]:checked')?.value;
    if (modalidade === 'entrega') {
      const bairroDigitado = inputBairroBusca?.value?.trim();
      if (!bairroDigitado) {
        marcarErro(inputBairroBusca, 'erro-entrega-bairro', 'Informe ou selecione seu bairro para entrega.');
      } else if ((inputBairroHidden?.value === 'outro' || bairroDigitado.toLowerCase() === 'outro bairro') && !inputOutroBairro?.value?.trim()) {
        marcarErro(inputOutroBairro, 'erro-entrega-bairro', 'Informe o nome do seu bairro no campo abaixo.');
      }

      if (!inputRua?.value?.trim()) {
        marcarErro(inputRua, 'erro-entrega-rua', 'Informe o nome da rua ou avenida.');
      }
      if (!inputNumero?.value?.trim()) {
        marcarErro(inputNumero, 'erro-entrega-numero', 'Informe o número do local.');
      }
    }

    // Validar Troco se Dinheiro
    const formaPag = document.querySelector('input[name="forma_pagamento"]:checked')?.value;
    const precisaTroco = document.querySelector('input[name="precisa_troco"]:checked')?.value;
    if (formaPag === 'dinheiro' && precisaTroco === 'sim') {
      if (!inputValorTroco?.value?.trim()) {
        marcarErro(inputValorTroco, 'erro-valor-troco', 'Informe para quanto precisa de troco.');
      } else {
        const vPago = extrairNumeroMoeda(inputValorTroco.value);
        const subtotal = carrinho.obterSubtotal();
        const promo = obterPromocaoAtiva(config.promocao);
        const desc = promo.ativa ? promo.calcularDesconto(subtotal) : 0;
        const subDesc = Math.max(0, subtotal - desc);
        const mod = document.querySelector('input[name="modalidade_tipo"]:checked')?.value || 'entrega';
        const bairroH = inputBairroHidden?.value?.trim() || '';
        const bairroIn = inputBairroBusca?.value?.trim() || '';
        const bFinal = bairroH || bairroIn;
        const eInfo = calcularTaxaEntrega(mod, bFinal, bairrosLista);
        const tTaxa = mod === 'entrega' && typeof eInfo.taxa === 'number' ? eInfo.taxa : 0;
        const tot = subDesc + tTaxa;

        if (vPago > 0 && vPago < tot) {
          marcarErro(inputValorTroco, 'erro-valor-troco', `O valor para troco (${formatarPreco(vPago)}) deve ser maior que o total do pedido (${formatarPreco(tot)}).`);
        }
      }
    }

    if (!valido && primeiroElementoInvalido) {
      primeiroElementoInvalido.scrollIntoView({ behavior: 'smooth', block: 'center' });
      primeiroElementoInvalido.focus();
    }

    return valido;
  }

  // 9. ABRIR E FECHAR MODAL
  function abrir() {
    pararLenis();
    overlay?.classList.add('is-open');
    overlay?.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    // Restaura tela caso estivesse no pós-envio
    telaPosEnvioAtiva = false;
    if (telaPosEnvio) telaPosEnvio.style.display = 'none';
    if (footerModal) footerModal.style.display = 'flex';

    verificarStatusFuncionamento();
    renderizarItensModal();
    carregarDadosSalvos();
  }

  function fechar() {
    overlay?.classList.remove('is-open');
    overlay?.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    retomarLenis();
  }

  // Permite rolagem com o mouse
  const modalBody = document.querySelector('#pedido-modal-body');
  if (modalBody) {
    modalBody.addEventListener('wheel', (e) => {
      e.stopPropagation();
    }, { passive: true });
  }

  // Event Listeners de navegação
  btnFechar?.addEventListener('click', fechar);
  overlay?.addEventListener('click', (e) => {
    if (e.target === overlay) fechar();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay?.classList.contains('is-open')) {
      fechar();
    }
  });

  btnAddMais?.addEventListener('click', () => {
    fechar();
    const cardapio = document.querySelector('#cardapio');
    cardapio?.scrollIntoView({ behavior: 'smooth' });
  });

  btnIrCardapio?.addEventListener('click', () => {
    fechar();
    const cardapio = document.querySelector('#cardapio');
    cardapio?.scrollIntoView({ behavior: 'smooth' });
  });

  // 10. ENVIO DO PEDIDO (SISTEMA + TELA PÓS-ENVIO + ACOMPANHAMENTO)
  let enviandoPedido = false;
  // Reaproveitada nas novas tentativas: se o servidor salvou mas a resposta se perdeu, não duplica o pedido
  let chaveIdempotencia = null;
  btnEnviar?.addEventListener('click', async () => {
    // Evita pedido duplicado por clique duplo enquanto o envio anterior não terminou
    if (enviandoPedido) return;

    if (carrinho.obterItens().length === 0) {
      alert('Seu carrinho está vazio. Adicione itens antes de enviar!');
      return;
    }

    // Revalidação em tempo real do horário no momento do envio (TAREFA 5)
    const statusAgora = verificarStatusFuncionamento();
    if (!statusAgora.podeFazerPedido) {
      alert(`A pizzaria acabou de encerrar os pedidos para hoje (${statusAgora.statusTexto}). Não é possível enviar novos pedidos no momento.`);
      return;
    }

    if (!validarFormulario()) {
      return;
    }

    enviandoPedido = true;
    if (btnEnviar) btnEnviar.disabled = true;
    if (btnEnviarLabel) btnEnviarLabel.textContent = 'Enviando pedido...';

    // Obter dados do formulário
    const dados = obterDadosFormulario();
    chaveIdempotencia = chaveIdempotencia || `idemp_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    dados.idempotencyKey = chaveIdempotencia;
    // O backend lê o cupom em "cupom"; a promoção do site é aplicada automaticamente
    dados.cupom = dados.promocaoInfo?.ativa ? (dados.promocaoInfo.cupom || '') : '';

    // Salvar dados no localStorage para próximas compras (TAREFA 6)
    salvarDadosCliente(dados);

    // O pedido só existe se o sistema registrar: sem resposta, o cliente tenta de novo
    let resBackend;
    try {
      resBackend = await criarPedidoApi(dados);
    } catch (errBackend) {
      const semConexao = !errBackend.status;
      alert(semConexao
        ? 'Não conseguimos enviar seu pedido agora. Verifique sua internet e tente novamente.'
        : `Não foi possível enviar o pedido: ${errBackend.message}`);
      return;
    } finally {
      enviandoPedido = false;
      if (btnEnviar) btnEnviar.disabled = false;
      verificarStatusFuncionamento();
    }

    const codigoPedido = resBackend.codigoPedido;
    chaveIdempotencia = null;
    registrarPedidoRecente({ codigo: codigoPedido, total: resBackend.total, modalidade: dados.modalidade });

    // Exibir Tela Pós-Envio (TAREFA 4)
    telaPosEnvioAtiva = true;
    carrinho.limparCarrinho();
    if (avisoVazio) avisoVazio.style.display = 'none';
    if (conteudoAtivo) conteudoAtivo.style.display = 'none';
    if (footerModal) footerModal.style.display = 'none';
    if (telaPosEnvio) telaPosEnvio.style.display = 'block';

    if (posCodigoDisplay) posCodigoDisplay.textContent = codigoPedido;

    // Botão de acompanhamento do pedido
    const btnAcompanharRastreio = document.querySelector('#btn-acompanhar-rastreio');
    if (btnAcompanharRastreio) {
      btnAcompanharRastreio.onclick = () => {
        fechar();
        window.abrirModalRastreio?.(codigoPedido);
      };
    }

    const pixConfig = config.pagamento?.pix || {};
    if (dados.pagamento.forma === 'pix') {
      if (posPixCard) posPixCard.style.display = 'block';
      if (posOutrosCard) posOutrosCard.style.display = 'none';
      if (posPixTipo) posPixTipo.textContent = pixConfig.tipo || 'Chave Pix';
      if (posPixChave) posPixChave.textContent = pixConfig.chave || '(65) 99265-0139';
    } else {
      if (posPixCard) posPixCard.style.display = 'none';
      if (posOutrosCard) posOutrosCard.style.display = 'block';
      if (posOutrosMsg) {
        const tempoMsg = dados.modalidade === 'retirada'
          ? (config.operacional?.tempoRetirada || config.pagamento?.tempoMedioRetirada || '20 a 35 min')
          : (config.operacional?.tempoEntrega || config.pagamento?.tempoMedioEspera || '40 min');
        posOutrosMsg.textContent = `A pizzaria vai conferir e confirmar seu pedido em instantes. Tempo médio após a confirmação: ${tempoMsg}.`;
      }
    }

    // Rola para o topo do corpo do modal
    modalBody?.scrollTo({ top: 0, behavior: 'smooth' });
  });


  // Copiar Chave Pix com Fallback (TAREFA 4)
  btnCopiarPix?.addEventListener('click', async () => {
    const chave = config.pagamento?.pix?.chave || posPixChave?.textContent || '';
    let copiado = false;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(chave);
        copiado = true;
      } catch (e) {
        copiado = false;
      }
    }

    if (!copiado) {
      // Fallback com textarea temporário
      const tempArea = document.createElement('textarea');
      tempArea.value = chave;
      tempArea.style.position = 'fixed';
      tempArea.style.opacity = '0';
      document.body.appendChild(tempArea);
      tempArea.select();
      try {
        copiado = document.execCommand('copy');
      } catch (e) {
        copiado = false;
      }
      document.body.removeChild(tempArea);
    }

    if (btnCopiarPixLabel) {
      btnCopiarPixLabel.textContent = copiado ? '✓ Chave Copiada!' : 'Chave: ' + chave;
      setTimeout(() => {
        if (btnCopiarPixLabel) btnCopiarPixLabel.textContent = 'Copiar Chave';
      }, 3000);
    }
  });

  // Botão Fazer Outro Pedido
  btnNovoPedido?.addEventListener('click', () => {
    telaPosEnvioAtiva = false;
    if (telaPosEnvio) telaPosEnvio.style.display = 'none';
    fechar();
    document.querySelector('#cardapio')?.scrollIntoView({ behavior: 'smooth' });
  });

  // Sincronização de eventos globais
  window.addEventListener('carrinho-atualizado', renderizarItensModal);
  window.addEventListener('abrir-modal-checkout', abrir);
  window.addEventListener('fechar-modal-checkout', fechar);
}
