// Backend API adresi — Web, Capacitor iOS, Android hepsinde çalışır.
//
// WEB: '' (aynı origin) — hem lokalde (Vite proxy) hem canlıda (Render aynı
//      servis hem siteyi hem API'yi sunar) CORS sorunu olmaz.
//
// iPHONE/ANDROID (Capacitor): Render'daki canlı backend URL'si.
//      Render'da servis adını değiştirirsen burayı güncelle!
const PRODUCTION_API_URL = 'https://lumiere-api.onrender.com';

const getApiBase = () => {
  if (typeof window !== 'undefined' && window.Capacitor) {
    return PRODUCTION_API_URL;
  }
  // Tarayıcıda aynı origin üzerinden gider (lokalde Vite proxy'si devrede).
  return '';
};

export const API_BASE = getApiBase();
