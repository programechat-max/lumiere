// Girdi doğrulama yardımcıları (PROMPT 8). Login.jsx/Register.jsx'teki tekrarlı
// inline mantığın merkezi hali - tek yerden güncellenip her formda tutarlı çalışır.
// NOT: Bunlar sadece KULLANICI DENEYİMİ içindir (anında geri bildirim). Gerçek
// güvenlik doğrulaması her zaman backend'de (Pydantic + auth.validate_password_strength)
// yapılır - istemci tarafı kontrolüne asla güvenilmez.

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(email) {
  return EMAIL_REGEX.test(String(email || '').trim());
}

export function getPasswordStrength(password) {
  if (!password) return 0;
  let strength = 0;
  if (password.length >= 8) strength++;
  if (/[a-z]/.test(password)) strength++;
  if (/[A-Z]/.test(password)) strength++;
  if (/[0-9]/.test(password)) strength++;
  if (/[^A-Za-z0-9]/.test(password)) strength++;
  return strength;
}

// Backend PROMPT 2 kuralıyla hizalı (min 12 karakter + karmaşıklık). Formlarda
// hâlâ 8 karakterlik daha yumuşak bir minimum kabul ediyoruz (mevcut kullanıcı
// deneyimini bozmamak için); backend nihai otoriteyi her zaman elinde tutar ve
// zayıf şifreleri 422 ile reddeder.
export function validatePasswordForSignup(password) {
  if (!password) return 'Şifre zorunludur';
  if (password.length < 8) return 'Şifre en az 8 karakter olmalı';
  return null;
}

export function validateEmailField(email) {
  if (!email) return 'E-posta adresi zorunludur';
  if (!isValidEmail(email)) return 'Geçerli bir e-posta adresi girin';
  return null;
}

export function validateFullName(name) {
  const trimmed = String(name || '').trim();
  if (!trimmed) return 'Ad ve soyad zorunludur';
  if (trimmed.length < 2) return 'Ad ve soyad en az 2 karakter olmalı';
  return null;
}

// Basit sınıflandırma yardımcıları (fetch/network hatası mı, HTTP hatası mı?)
export function isNetworkError(err) {
  return err?.name === 'AbortError' || /Failed to fetch|NetworkError/i.test(err?.message || '');
}
