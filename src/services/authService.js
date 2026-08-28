// Kimlik doğrulama servisi (PROMPT 2 & PROMPT 8).
//
// Backend artık iki paralel akış sunuyor:
//  - Legacy: /api/auth/* -> access_token'ı gövdede döner (cookie yok).
//  - Yeni:   /api/v1/auth/* -> access_token'ı gövdede döner AMA AYRICA HttpOnly
//            refresh-token cookie'si + JS'in okuyabildiği csrf_token cookie'si set eder.
//            Bu sayede uzun ömürlü kimlik bilgisi (refresh token) artık
//            localStorage'da DEĞİL, XSS'e karşı korumalı bir HttpOnly cookie'de tutulur.
//
// Bu servis YENİ (/api/v1) akışı kullanır. Access token'ı öncelikle BELLEKTE
// (modül değişkeni) tutar; localStorage'a sadece geriye dönük uyumluluk için
// (App.jsx'in geri kalanı henüz bu servise taşınmadığından) bir "ayna" kopyası
// yazılır - bu, App.jsx'i büyük ölçüde yeniden yazmadan güvenlik iyileştirmesi
// yapabilmemizi sağlayan kasıtlı bir geçiş stratejisidir (bkz. docs/SECURITY.md).
import { API_BASE } from '../config';

const AUTH_BASE = `${API_BASE}/api/v1/auth`;
const CSRF_COOKIE_NAME = 'csrf_token';

let inMemoryAccessToken = null;
let refreshTimerId = null;

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function persistSession(accessToken, user) {
  inMemoryAccessToken = accessToken;
  try {
    // Geriye dönük uyumluluk aynası - App.jsx'in mevcut localStorage okumaları
    // için (bkz. src/App.jsx). Gerçek uzun ömürlü kimlik bilgisi (refresh token)
    // ASLA buraya yazılmaz, sadece kısa ömürlü (15dk) access token yazılır.
    localStorage.setItem('token', accessToken);
    if (user) localStorage.setItem('user', JSON.stringify(user));
  } catch {
    // localStorage kapalı/dolu olsa bile bellekteki token ile oturum çalışmaya devam eder.
  }
  scheduleAutoRefresh();
}

function clearSession() {
  inMemoryAccessToken = null;
  if (refreshTimerId) {
    clearTimeout(refreshTimerId);
    refreshTimerId = null;
  }
  try {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  } catch {
    /* no-op */
  }
}

/** Access token'ın süresi dolmadan (14. dakikada) sessizce yeniler - kullanıcı
 * uzun bir dashboard oturumunda aniden 401 ile karşılaşmasın. */
function scheduleAutoRefresh() {
  if (refreshTimerId) clearTimeout(refreshTimerId);
  refreshTimerId = setTimeout(() => {
    refreshAccessToken().catch(() => {
      /* sessizce başarısız ol - bir sonraki API çağrısı zaten 401 alıp login'e yönlendirecek */
    });
  }, 14 * 60 * 1000);
}

async function parseErrorDetail(res, fallback) {
  try {
    const body = await res.json();
    return body.detail || body?.error?.message || fallback;
  } catch {
    return `Sunucu hatası (${res.status})`;
  }
}

export async function login(email, password) {
  const res = await fetch(`${AUTH_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include', // HttpOnly refresh/csrf cookie'lerini almak için ZORUNLU
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res, 'Giriş başarısız oldu.'));
  const data = await res.json();
  persistSession(data.access_token, data.user);
  return data.user;
}

export async function register(fullName, email, password, preferredPlan = 'FREE') {
  const res = await fetch(`${AUTH_BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ full_name: fullName, email, password, preferred_plan: preferredPlan }),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res, 'Kayıt başarısız oldu.'));
  const data = await res.json();
  persistSession(data.access_token, data.user);
  return data.user;
}

export async function refreshAccessToken() {
  const csrfToken = readCookie(CSRF_COOKIE_NAME);
  const res = await fetch(`${AUTH_BASE}/refresh`, {
    method: 'POST',
    credentials: 'include',
    headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
  });
  if (!res.ok) {
    clearSession();
    throw new Error('Oturum süresi doldu.');
  }
  const data = await res.json();
  inMemoryAccessToken = data.access_token;
  try {
    localStorage.setItem('token', data.access_token);
  } catch {
    /* no-op */
  }
  scheduleAutoRefresh();
  return data.access_token;
}

export async function logout() {
  try {
    await fetch(`${AUTH_BASE}/logout`, { method: 'POST', credentials: 'include' });
  } catch {
    /* çevrimdışı olsa bile yerel oturumu temizle */
  } finally {
    clearSession();
  }
}

/** Bellekteki token varsa onu, yoksa (örn. sayfa yenilendi) localStorage aynasını döner. */
export function getAccessToken() {
  if (inMemoryAccessToken) return inMemoryAccessToken;
  try {
    return localStorage.getItem('token');
  } catch {
    return null;
  }
}

export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null');
  } catch {
    return null;
  }
}

export function isAuthenticated() {
  return !!getAccessToken();
}

export { clearSession as clearLocalSession };
