/**
 * API Client para Don Corleone
 *
 * Comunicação com o backend Django sob /api/v1/
 * Inclui tolerância a falhas (fallback gracioso para dados locais caso backend offline).
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Sem resposta neste tempo a requisição é abortada (no envio do pedido, o cliente tenta de novo)
const TEMPO_LIMITE_MS = 8000;

export async function requestApi(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    ...(options.headers || {})
  };

  // Add auth token if customer is logged in
  let token = null;
  try {
    token = localStorage.getItem('don_corleone_auth_token');
  } catch (e) {
    token = null;
  }
  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs || TEMPO_LIMITE_MS);

  const config = {
    ...options,
    headers,
    signal: controller.signal
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      // Erros inesperados já vêm com uma frase amigável e o código da ocorrência (ERR-...);
      // sem corpo JSON (servidor fora do ar) usamos uma frase genérica, nunca o código HTTP cru
      const semDetalhe = response.status >= 500
        ? 'O sistema da pizzaria está com uma instabilidade. Tente de novo em instantes.'
        : 'Não foi possível concluir. Confira os dados e tente de novo.';
      const error = new Error(extrairMensagemErro(errorData) || semDetalhe);
      error.status = response.status;
      error.data = errorData;
      throw error;
    }
    return await response.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      err.message = 'O servidor demorou para responder.';
    }
    console.warn(`[API Client] Falha ao comunicar com endpoint ${endpoint}:`, err.message);
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Converte o formato de erro do Django REST Framework em uma frase legível.
 * Ex.: {"whatsapp": ["Este WhatsApp já está cadastrado."]} -> "Este WhatsApp já está cadastrado."
 */
function extrairMensagemErro(errorData) {
  if (!errorData || typeof errorData !== 'object') return '';
  const direta = errorData.detail || errorData.error || errorData.message || errorData.mensagem;
  if (direta) return String(direta);

  for (const valor of Object.values(errorData)) {
    if (Array.isArray(valor) && valor.length) return String(valor[0]);
    if (typeof valor === 'string') return valor;
  }
  return '';
}
