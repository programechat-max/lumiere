// Telefon/App Store icin URETIM build'i.
//
// Neden bu script var?
// Vite, proje kokundeki `.env.local` dosyasini HER build'e otomatik yukler.
// Bu makinede `.env.local` gelistirme amacli `VITE_CAPACITOR_API_URL=http://192.168.x.x:8000`
// iceriyordu ve telefona giden bundle'a LAN IP'si (ya da gecici tunel adresi) gomuluyordu.
// Sonuc: uygulama sadece Mac ile ayni Wi-Fi'dayken calisiyor, disari cikinca
// "Sunucuya baglanilamadi" hatasi veriyordu.
//
// Bu script build'i izole/temiz bir ortamda calistirir ve uretilen bundle'I
// dogrular: yalnizca canli Render API'si gomulu olmali, LAN IP/tunel OLMAMALI.
import { spawnSync } from 'node:child_process';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const PROD_HOST = 'lumiere-api-ea82.onrender.com';
const DIST_ASSETS = new URL('../dist/assets/', import.meta.url).pathname;

// 1) Izole ortamda build: VITE_* disinda gelistirici kabugundan sizan hicbir
//    degisken gecmesin. (.env.local yine de Vite tarafindan okunabilir; o
//    yuzden asagida icerik dogrulamasi yapiyoruz.)
const env = {
  PATH: process.env.PATH,
  HOME: process.env.HOME,
  NODE_ENV: 'production',
};
// Gelistirici kabugunda yanlislikla set edilmis VITE_* degiskenlerini TEMIZLE.
// Boylece `npm run build:release` her zaman canli API'yi gomer.
for (const key of Object.keys(process.env)) {
  if (key.startsWith('VITE_')) delete env[key];
}

console.log('[build:release] Temiz uretim build i aliniyor...');
const build = spawnSync('npx', ['vite', 'build'], { env, stdio: 'inherit' });
if (build.status !== 0) {
  console.error('[build:release] Vite build basarisiz oldu.');
  process.exit(build.status ?? 1);
}

// 2) Bundle dogrulamasi: canli API gomulu olmali, LAN/tunel OLMAMALI.
const jsFiles = readdirSync(DIST_ASSETS).filter((f) => f.endsWith('.js'));
if (jsFiles.length === 0) {
  console.error('[build:release] dist/assets icinde JS bundle bulunamadi!');
  process.exit(1);
}

const forbidden = [
  /192\.168\.\d+\.\d+/,
  /10\.\d+\.\d+\.\d+/,
  /127\.0\.0\.1/,
  /localhost:8000/,
  /trycloudflare\.com/,
  /ngrok-free\.(dev|app|io)/,
];

let ok = true;
for (const file of jsFiles) {
  const code = readFileSync(join(DIST_ASSETS, file), 'utf8');
  for (const pattern of forbidden) {
    const hit = code.match(pattern);
    if (hit) {
      console.error(`[build:release] HATA: ${file} icinde yasak adres bulundu -> ${hit[0]}`);
      ok = false;
    }
  }
  if (!code.includes(PROD_HOST)) {
    console.error(`[build:release] HATA: ${file} canli API adresini (${PROD_HOST}) icermiyor.`);
    ok = false;
  }
}

if (!ok) {
  console.error('\n[build:release] Bundle dogrulamasi BASARISIZ. Muhtemel neden:');
  console.error('  - Proje kokundeki .env.local icinde VITE_CAPACITOR_API_URL tanimli.');
  console.error('    Bu dosya telefon build ine siziyor. Uretim icin kaldirilmali ya da');
  console.error('    bu degisken icermemeli (gelistirme tercihlerinizi .env.development.local a tasiyin).');
  process.exit(1);
}

console.log(`[build:release] OK - bundle yalnizca canli API ye (${PROD_HOST}) isaret ediyor.`);
console.log('[build:release] Simdi iOS a senkronlayin: npx cap sync ios');
