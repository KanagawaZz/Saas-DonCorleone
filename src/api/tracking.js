import { requestApi } from './client.js';

export async function buscarRastreioPedidoApi(codigo) {
  return await requestApi(`/tracking/${encodeURIComponent(codigo)}/`);
}
