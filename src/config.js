// Backend API adresi — Web, Capacitor iOS, Android hepsinde çalışır.
//
// WEB: '' (aynı origin) — hem lokalde (Vite proxy) hem canlıda (Render aynı
//      servis hem siteyi hem API'yi sunar) CORS sorunu olmaz.
//
// iPHONE/ANDROID (Capacitor): Render'daki canlı backend URL'si.
//      Render'da servis adını değiştirirsen burayı güncelle!
const PRODUCTION_API_URL = 'https://lumiere-api-ea82.onrender.com';
// iOS fiziksel cihaz testi için build sırasında LAN adresi verilebilir:
// VITE_CAPACITOR_API_URL=http://192.168.x.x:8000 npm run build
const CAPACITOR_API_URL = import.meta.env.VITE_CAPACITOR_API_URL || PRODUCTION_API_URL;

const getApiBase = () => {
  if (typeof window !== 'undefined') {
    // Native Capacitor builds normally expose `window.Capacitor`.  A static
    // file:// build (or a WKWebView during the very first boot) may not expose
    // it yet; using the same absolute API in those cases prevents requests
    // from silently going to file:///api/... and leaving media in a permanent
    // “analiz ediliyor” state.
    const protocol = window.location?.protocol;
    const isNativeShell = Boolean(window.Capacitor)
      || protocol === 'capacitor:'
      || protocol === 'ionic:'
      || protocol === 'file:';
    if (isNativeShell) {
      return CAPACITOR_API_URL;
    }
  }
  // Tarayıcıda aynı origin üzerinden gider (lokalde Vite proxy'si devrede).
  return '';
};

export const API_BASE = getApiBase();
