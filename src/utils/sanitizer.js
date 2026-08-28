// XSS önleme yardımcıları (PROMPT 8). React, JSX metin içeriğini varsayılan
// olarak escape ettiği için `{value}` kullanan normal render'lar zaten güvenlidir.
// Bu yardımcılar sadece (a) HTML string OLARAK render edilmesi gereken nadir
// durumlar (örn. gelecekte eklenebilecek zengin metin/bildirim içeriği) veya
// (b) kullanıcı girdisini bir URL/deep-link olarak kullanmadan önce doğrulamak
// için vardır.

const HTML_ESCAPE_MAP = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

/** Bir metni HTML'e güvenli şekilde gömülebilir hale getirir. */
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => HTML_ESCAPE_MAP[ch]);
}

/**
 * Push bildirimi/deep-link gibi sunucudan gelen bir yönlendirme hedefinin
 * uygulama İÇİ bir yol olduğunu doğrular (örn. "/workout/active"). Mutlak
 * URL'leri (javascript:, https://kötü-site.com) reddeder - açık yönlendirme
 * (open redirect) ve JS injection riskini önler.
 */
export function isSafeInternalPath(path) {
  if (typeof path !== 'string' || !path.startsWith('/')) return false;
  if (path.startsWith('//')) return false; // protokolsüz mutlak URL (//evil.com)
  return !/^\/(javascript|data):/i.test(path);
}

/** Dosya yükleme öncesi istemci tarafı MIME/uzantı kontrolü (savunma derinliği - asıl doğrulama backend'de). */
export function isAllowedUploadType(file, allowedPrefixes = ['image/', 'video/', 'audio/']) {
  if (!file || !file.type) return false;
  return allowedPrefixes.some((prefix) => file.type.startsWith(prefix));
}
