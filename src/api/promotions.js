import { requestApi } from './client.js';

export async function validarCupomApi(cupomCodigo, subtotal) {
  try {
    return await requestApi('/promotions/validate/', {
      method: 'POST',
      body: JSON.stringify({
        coupon_code: cupomCodigo,
        subtotal: subtotal
      })
    });
  } catch (err) {
    throw err;
  }
}

export async function carregarBannerPromocionalApi() {
  try {
    return await requestApi('/promotions/banner/');
  } catch (e) {
    return { ativa: false };
  }
}
