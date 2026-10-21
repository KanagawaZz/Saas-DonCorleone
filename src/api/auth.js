import { requestApi } from './client.js';

export async function cadastrarClienteApi(dados) {
  const res = await requestApi('/accounts/register/', {
    method: 'POST',
    body: JSON.stringify(dados)
  });
  if (res.token) {
    localStorage.setItem('don_corleone_auth_token', res.token);
    localStorage.setItem('don_corleone_user_data', JSON.stringify(res.user));
  }
  return res;
}

export async function loginClienteApi(username, password) {
  const res = await requestApi('/accounts/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
  if (res.token) {
    localStorage.setItem('don_corleone_auth_token', res.token);
    localStorage.setItem('don_corleone_user_data', JSON.stringify(res.user));
  }
  return res;
}

export function logoutCliente() {
  localStorage.removeItem('don_corleone_auth_token');
  localStorage.removeItem('don_corleone_user_data');
}

export function obterUsuarioLogado() {
  try {
    const raw = localStorage.getItem('don_corleone_user_data');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}
