// Güvenli API istemcisi (PROMPT 8): zaman aşımı, geçici hatalarda üstel geri
// çekilmeli tekrar deneme, 401'de otomatik token yenileme + tek seferlik tekrar
// deneme, ve kullanıcıya backend iç detaylarını sızdırmayan tutarlı hata mesajları.
import { API_BASE } from '../config';
import { getAccessToken, refreshAccessToken, clearLocalSession } from './authService';

const isCapacitor = () => typeof window !== 'undefined' && !!window.Capacitor;

const DEFAULT_TIMEOUT_MS = 30_000;

function buildRequestId() {
  return (crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`);
}

async function extractErrorMessage(res, fallback) {
  try {
    const body = await res.json();
    return body.detail || body?.error?.message || fallback;
  } catch {
    return fallback;
  }
}

/**
 * @param {string} path - Örn. "/api/v1/notifications/settings" (API_BASE otomatik eklenir)
 * @param {RequestInit & { timeoutMs?: number, retries?: number, skipAuth?: boolean }} options
 */
export async function apiFetch(path, options = {}) {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    retries = 2,
    skipAuth = false,
    headers: extraHeaders = {},
    ...fetchOptions
  } = options;

  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const requestId = buildRequestId();

  const doFetch = async (accessToken) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, {
        ...fetchOptions,
        credentials: fetchOptions.credentials ?? (isCapacitor() ? 'omit' : 'include'),
        signal: controller.signal,
        headers: {
          ...(fetchOptions.body && !(fetchOptions.body instanceof FormData)
            ? { 'Content-Type': 'application/json' }
            : {}),
          'X-Request-ID': requestId,
          ...(accessToken && !skipAuth ? { Authorization: `Bearer ${accessToken}` } : {}),
          ...extraHeaders,
        },
      });
    } finally {
      clearTimeout(timeoutId);
    }
  };

  let attempt = 0;
  let lastError = null;

  while (attempt <= retries) {
    try {
      let res = await doFetch(getAccessToken());

      // 401 -> token'ı bir kez yenilemeyi dene, sonra isteği tekrarla.
      if (res.status === 401 && !skipAuth) {
        try {
          const newToken = await refreshAccessToken();
          res = await doFetch(newToken);
        } catch {
          clearLocalSession();
          window.dispatchEvent(new CustomEvent('lumiere:session-expired'));
          throw new Error('Oturum süresi doldu, lütfen tekrar giriş yapın.');
        }
      }

      if (res.status === 429) {
        const retryAfter = Number(res.headers.get('Retry-After') || 5);
        throw Object.assign(new Error('Çok fazla istek gönderildi, lütfen biraz sonra tekrar deneyin.'), { retryAfter, status: 429 });
      }

      if (!res.ok) {
        const message = await extractErrorMessage(res, `Sunucu hatası (${res.status})`);
        throw Object.assign(new Error(message), { status: res.status });
      }

      const contentType = res.headers.get('content-type') || '';
      return contentType.includes('application/json') ? res.json() : res;
    } catch (err) {
      lastError = err;
      const isNetworkIssue = err.name === 'AbortError' || /Failed to fetch|NetworkError/i.test(err.message);
      const isRetryable = isNetworkIssue && attempt < retries;
      if (!isRetryable) break;
      await new Promise((resolve) => setTimeout(resolve, 2 ** attempt * 300)); // 300ms, 600ms, ...
      attempt += 1;
    }
  }

  if (lastError?.name === 'AbortError') {
    throw new Error('Sunucu yanıt vermedi (zaman aşımı). Backend servisinin çalıştığından emin olun.');
  }
  if (/Failed to fetch|NetworkError/i.test(lastError?.message || '')) {
    throw new Error(`Backend sunucusuna ulaşılamadı (${API_BASE}). Lütfen sunucuyu başlatın.`);
  }
  throw lastError;
}
