/**
 * Pedidos feitos neste aparelho, para o cliente reencontrar o acompanhamento
 * mesmo depois de fechar a aba. Fica só no navegador (localStorage).
 */

const STORAGE_KEY = 'don_corleone_pedidos_recentes_v1';
const MAX_PEDIDOS = 5;
// Pedidos mais antigos que isso já não interessam para acompanhamento
const VALIDADE_MS = 2 * 24 * 60 * 60 * 1000;

export function obterPedidosRecentes() {
  try {
    const lista = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    if (!Array.isArray(lista)) return [];
    const limite = Date.now() - VALIDADE_MS;
    return lista.filter(p => p && p.codigo && p.criadoEm > limite);
  } catch (e) {
    return [];
  }
}

export function registrarPedidoRecente({ codigo, total, modalidade }) {
  if (!codigo) return;
  try {
    const lista = obterPedidosRecentes().filter(p => p.codigo !== codigo);
    lista.unshift({ codigo, total, modalidade, criadoEm: Date.now() });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lista.slice(0, MAX_PEDIDOS)));
  } catch (e) {
    // Sem localStorage o cliente ainda acompanha pelo código exibido na tela
  }
}
