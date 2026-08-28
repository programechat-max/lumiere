// Merkezi hata işleme (PROMPT 8). Sentry DSN'i frontend'e henüz bağlanmadı
// (bkz. docs/SECURITY.md) - bu modül, o entegrasyon eklendiğinde TEK bir yerden
// devreye girecek şekilde tasarlandı (`setErrorReporter`). Şu an konsola loglar
// ve kullanıcıya her zaman güvenli, jenerik bir mesaj döndürür.

let reporter = (error, context) => {
  console.error('[Lumiere]', context?.scope || 'error', error);
};

/** Sentry vb. bir sağlayıcı bağlanmak istendiğinde çağrılır, örn:
 *  setErrorReporter((err, ctx) => Sentry.captureException(err, { extra: ctx })) */
export function setErrorReporter(fn) {
  reporter = fn;
}

export function reportError(error, context = {}) {
  try {
    reporter(error, context);
  } catch {
    /* raporlayıcının kendisi patlarsa uygulamayı etkilememeli */
  }
}

/** API/network hatalarını kullanıcıya gösterilecek güvenli bir mesaja çevirir.
 * Backend URL'leri veya stack trace ASLA kullanıcıya gösterilmez. */
export function toUserMessage(error, fallback = 'Bir şeyler ters gitti, lütfen tekrar deneyin.') {
  if (!error) return fallback;
  // apiClient.js zaten kullanıcı-dostu mesajlar üretiyor (bkz. extractErrorMessage);
  // burada sadece son bir güvenlik ağı olarak stack/URL sızıntısı temizleniyor.
  const message = String(error.message || fallback);
  if (/^(TypeError|ReferenceError|SyntaxError):/.test(message)) return fallback;
  return message;
}

export function installGlobalHandlers() {
  window.addEventListener('unhandledrejection', (event) => {
    reportError(event.reason, { scope: 'unhandledrejection' });
  });
  window.addEventListener('error', (event) => {
    reportError(event.error || event.message, { scope: 'window.onerror' });
  });
}
