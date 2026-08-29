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

function networkDiagError(url, err) {
  // WKWebView ag hatalarini "Load failed" diye dondurur - kullaniciya ve
  // teshise yardimci zengin mesaj uret.
  const online = (typeof navigator !== 'undefined' && navigator.onLine !== undefined) ? navigator.onLine : 'bilinmiyor';
  console.error('[Lumiere][AG] fetch basarisiz:', JSON.stringify({
    url, online, name: err?.name, message: err?.message,
  }));
  if (err?.name === 'AbortError') {
    return new Error(
      `Sunucu çok yavaş yanıt verdi (uyanıyor olabilir).\n` +
      `• Adres: ${url}\n\n` +
      `Telefonda bir dakika bekleyip tekrar dene. Kalıcı çözüm için sunucuyu\n` +
      `sürekli uyanık tutan ücretsiz bir izleme (örn. cron-job.org 5 dk HTTP ping) kur.`
    );
  }
  return new Error(
    `Sunucuya bağlanılamadı.\n` +
    `• Adres: ${url}\n` +
    `• İnternet: ${online === true ? 'var gibi' : online}\n\n` +
    `Şunları dene: Wi-Fi yerine mobil data (ya da tersini) dene; VPN açıksa kapat.`
  );
}

const REGISTER_TIMEOUT_MS = 120_000; // Render free soguk baslangic 40-120 sn surer
const REGISTER_ATTEMPTS = 3;

export async function register(fullName, email, password, preferredPlan = 'FREE') {
  const url = `${AUTH_BASE}/register`;
  // Render free plani islem yoksa uyur (soguk baslangic 40-120 sn). Bu yuzden
  // 120 sn timeout + 3 deneme ile soguk baslangica karsi dayanikliyiz.
  let lastErr = null;
  for (let attempt = 1; attempt <= REGISTER_ATTEMPTS; attempt++) {
    let res;
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), REGISTER_TIMEOUT_MS);
      try {
        res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          signal: controller.signal,
          body: JSON.stringify({ full_name: fullName, email, password, preferred_plan: preferredPlan }),
        });
      } finally {
        clearTimeout(timer);
      }
    } catch (err) {
      lastErr = err;
      if (attempt < REGISTER_ATTEMPTS) {
        await new Promise(r => setTimeout(r, 4000)); // soguk baslangic icin bekle ve tekrar dene
        continue;
      }
      throw networkDiagError(url, err);
    }
    if (!res.ok) throw new Error(await parseErrorDetail(res, 'Kayıt başarısız oldu.'));
    const data = await res.json();
    persistSession(data.access_token, data.user);
    return data.user;
  }
  throw networkDiagError(url, lastErr);
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
