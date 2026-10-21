/**
 * Dados do site vindos do banco (painel do dono)
 *
 * Antes de montar a página, busca no backend o cardápio, bordas, bairros, horários,
 * pagamento e promoção. Os dados chegam no mesmo formato dos arquivos locais
 * (cardapio.json, bairros.json, compre-junto.json, site.config.js) e são copiados
 * PARA DENTRO desses mesmos objetos: todos os componentes que já os importam passam a
 * enxergar os valores do painel sem nenhuma alteração.
 *
 * Se o backend não responder rápido, o site segue com os arquivos locais.
 */

import { requestApi } from './client.js';
import { siteConfig } from '../data/site.config.js';
import dadosCardapio from '../data/cardapio.json';
import bairrosLista from '../data/bairros.json';
import { ITENS_COMPRE_JUNTO } from '../data/compre-junto.js';

// O site espera este tempo antes de seguir com os dados locais
const TEMPO_LIMITE_MS = 2500;

function substituirLista(destino, novos) {
  destino.splice(0, destino.length, ...novos);
}

function aplicarDados(dados) {
  if (Array.isArray(dados.cardapio?.categorias) && dados.cardapio.categorias.length) {
    dadosCardapio.categorias = dados.cardapio.categorias;
  }

  if (Array.isArray(dados.bairros)) {
    substituirLista(bairrosLista, dados.bairros);
  }

  if (Array.isArray(dados.bordas) && dados.bordas.length && siteConfig.regrasPizza) {
    siteConfig.regrasPizza.bordas = dados.bordas;
  }

  if (Array.isArray(dados.horario?.dias) && dados.horario.dias.length && siteConfig.horario) {
    siteConfig.horario.dias = dados.horario.dias;
  }

  if (dados.pagamento) {
    const minimo = dados.pagamento.pedidoMinimo;
    if (typeof minimo === 'number') {
      siteConfig.pagamento.pedidoMinimo = minimo;
      if (siteConfig.regrasComerciais) siteConfig.regrasComerciais.pedidoMinimo = minimo;
    }
    if (dados.pagamento.pix) {
      siteConfig.pagamento.pix = { ...siteConfig.pagamento.pix, ...dados.pagamento.pix };
    }
  }

  if (dados.operacional) {
    siteConfig.operacional = { ...siteConfig.operacional, ...dados.operacional };
    if (dados.operacional.tempoRetirada) siteConfig.pagamento.tempoMedioRetirada = dados.operacional.tempoRetirada;
  }

  if (dados.promocao) {
    siteConfig.promocao = dados.promocao;
  }

  // Compre Junto: preço atualizado e itens esgotados saem das sugestões
  if (Array.isArray(dados.compreJunto)) {
    const porId = new Map(dados.compreJunto.map((item) => [item.id, item]));
    const atualizados = ITENS_COMPRE_JUNTO
      .filter((item) => porId.get(item.id)?.disponivel !== false)
      .map((item) => {
        const preco = porId.get(item.id)?.preco;
        return typeof preco === 'number' ? { ...item, preco } : item;
      });
    substituirLista(ITENS_COMPRE_JUNTO, atualizados);
  }
}

/**
 * Nunca lança erro: em qualquer falha o site continua com os dados locais.
 * @returns {Promise<boolean>} true se os dados do banco foram aplicados
 */
export async function carregarDadosDoBanco() {
  try {
    const dados = await requestApi('/catalog/site-data/', { timeoutMs: TEMPO_LIMITE_MS });
    aplicarDados(dados || {});
    return true;
  } catch (e) {
    console.info('[Dados do site] Usando dados locais:', e.message);
    return false;
  }
}
