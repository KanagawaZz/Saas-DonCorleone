import { requestApi } from './client.js';

export async function criarPedidoApi(dadosPedido) {
  try {
    const res = await requestApi('/orders/create/', {
      method: 'POST',
      body: JSON.stringify(dadosPedido)
    });
    return res;
  } catch (err) {
    console.warn('[Orders API] Não foi possível salvar pedido no backend:', err.message);
    throw err;
  }
}
