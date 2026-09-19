// Lumiere adım sayacı — DSP v2: desen doğrulamalı pedometre motoru.
//
// Cihaz ivmeölçerini (DeviceMotion) kullanır. v2'nin farkı, yürüyüş olmayan
// hareketleri (telefon kapma, el sallama, araba salınımı) adım saymamasıdır:
//
//   1) Yerçekimi EKSEN BAŞINA vektör olarak izlenir (gx,gy,gz) → lineer ivme
//      vektörünün normu alınır. Telefon döndüğünde yerçekimi eksenler
//      arasında kayar; yönelim değişimi (dot < ~25°) algılanınca 0.8 sn
//      tespit duraklatılır — dönüş artık sinyal üretmez.
//   2) Sinyalden yavaş taban çizgisi (B_ALPHA) çıkarılır → dalgalanma
//      (band-pass etkisi): düşük frekanslı araba salınımları sinyalde kalmaz.
//   3) Tepe tespiti ADAY üretir, anında adım SAYMAZ. Desen doğrulaması:
//      >=3 ardışık aday, dar pencere, aralık tutarlılığı (CV <= %45) ve
//      genlik tutarlılığı (maks/min <= 2.2). Doğrulanınca bekleyen adımlar
//      toplu sayılır; doğrulanmayan İZOLE adaylar atılır (telefon kapma = 0).
//   4) Yürüyüş onaylandıktan sonra adımlar teker teker sayılır; 2.5 sn
//      sessizlikte durum kapanır, zincir >1 sn bozulursa adaylar atılır.
//
// Adımlar StepSink ile store'a gider; günün toplamı vitalsMap'te kalıcıdır.
// process() aynı zamanda test kancasıdır (sentetik sinyal enjeksiyonu).
import { useSyncExternalStore } from 'react';

export type PedometerMode = 'idle' | 'walking' | 'running';
export type PedometerPermission = 'unknown' | 'granted' | 'denied' | 'unsupported';

export interface PedometerTelemetry {
  supported: boolean;        // cihazda DeviceMotion var mı
  permission: PedometerPermission;
  active: boolean;           // dinleyici açık
  sensorLive: boolean;       // ilk gerçek sensör örneği alındı mı
  needsGesture: boolean;     // iOS: izin için kullanıcı dokunuşu gerekli
  steps: number;             // bu oturumda sayılan (doğrulanmış) adım
  cadence: number;           // adım/dk (yumuşatılmış)
  mode: PedometerMode;
  distanceM: number;         // oturum mesafesi (m)
  kcal: number;              // oturum kalorisi
  strideM: number;           // güncel tahmini adım uzunluğu
  sensorHz: number;          // ölçülen örnekleme hızı
  pending: number;           // doğrulama bekleyen aday adım
  peakSigma: number;         // son tepe genliği (diagnostik)
}

/* --- ayarlar (Dengeli) --- */
const GA = 0.02;             // yerçekimi vektörü çok yavaş takip (step frekansını ve yön dalgalanmasını izlemez)
const B_ALPHA = 0.02;        // taban çizgisi low-pass (yavaş)
const S_ALPHA = 0.35;        // dalgalanma yumuşatma
const WINDOW = 96;           // adaptif pencere (~1.6 sn @60Hz)
const WARMUP = 24;           // pencere ısınma eşiği
const K_SIGMA = 0.75;        // eşik = ort + K_SIGMA*sigma
const MIN_AMP = 0.5;         // m/s² — taban üstü minimum tepe genliği (masa gürültüsü elenir)
const MIN_INTERVAL_MS = 235; // yürüme min adım aralığı
const MIN_INTERVAL_RUN_MS = 205;
const MAX_INTERVAL_MS = 1000;     // aradaki boşluk yürüyüş olamaz
const CADENCE_RUN = 152;          // bu kadans üstü koşu sayılır
const RUN_AMP = 2.6;              // koşu için sigma genlik eşiği
const IDLE_MS = 3200;             // bu kadar sessizlik -> idle
const WALK_TIMEOUT_MS = 2500;     // yürüyüş durumundan çıkış
const CONFIRM_N = 5;              // desen doğrulaması için min ardışık aday
const CONFIRM_WINDOW_MS = 2600;   // doğrulama penceresi
const INTERVAL_CV_MAX = 0.28;     // aralık tutarlılığı (std/ort)
const AMP_RATIO_MAX = 1.8;        // genlik tutarlılığı (maks/min)
const ROT_DOT_MIN = 0.99;         // ~8° üstü yönelim değişimi = dönüş
const ROT_PAUSE_MS = 800;         // dönüş sonrası tespit duraklatma
const ROT_FAST_MS = 3000;         // dönüş sonrası hızlı takip süresi (yeni eksene oturmak için)
const G_LIMIT = 25;               // m/s² — darbe/çarpma örneği reddi
const NOTIFY_MS = 400;            // UI bildirim periyodu
const WEIGHT_DEFAULT = 75;        // kg — store profilinden güncellenir

type StepSink = (delta: number) => void;
interface Candidate { t: number; amp: number }
interface DMEvent { accelerationIncludingGravity: { x: number | null; y: number | null; z: number | null } | null }
interface DMConstructor { requestPermission?: () => Promise<'granted' | 'denied'> }

export class PedometerEngine {
  private listeners = new Set<() => void>();
  private snap: PedometerTelemetry = {
    supported: false, permission: 'unknown', active: false, sensorLive: false, needsGesture: false,
    steps: 0, cadence: 0, mode: 'idle', distanceM: 0, kcal: 0, strideM: 0, sensorHz: 0, pending: 0, peakSigma: 0,
  };
  private sink: StepSink | null = null;

  // sinyal durumu
  private gx = 0; private gy = 0; private gz = 9.81;   // yerçekimi vektörü
  private pux = 0; private puy = 0; private puz = 1;    // önceki birim vektör
  private base = 0; private hasBase = false;            // taban çizgisi
  private s = 0;                                        // yumuşatılmış dalgalanma
  private buf: number[] = []; private sum = 0; private sumSq = 0;
  private armed = false; private candPeak = 0;
  private pend: Candidate[] = [];                       // doğrulama bekleyen adaylar
  private walking = false;                              // desen onaylı yürüyüş
  private walkingAmps: number[] = [];                   // yürüyüş tepe genlikleri (kalite denetimi)
  private lastCandAt = 0;
  private intervals: number[] = [];
  private rotUntil = 0;
  private rotFastUntil = 0;
  private baseUnitX = 0; private baseUnitY = 0; private baseUnitZ = 1; // yavaş referans (dönüş tespiti)
  private baseUnitAt = 0;
  private lastEvtAt = 0;
  private weight = WEIGHT_DEFAULT;
  private notifyTimer: number | null = null;
  private dirty = false;

  /* ---- reaktif arayüz (useSyncExternalStore) ---- */
  subscribe = (fn: () => void): (() => void) => {
    this.listeners.add(fn);
    return () => { this.listeners.delete(fn); };
  };
  getSnapshot = (): PedometerTelemetry => this.snap;

  private patch(p: Partial<PedometerTelemetry>) {
    this.snap = { ...this.snap, ...p };
  }
  private notify() {
    this.listeners.forEach((l) => l());
  }

  /* ---- genel API ---- */
  setStepSink(sink: StepSink | null) { this.sink = sink; }
  setUserWeight(kg: number) { if (kg > 25 && kg < 300) this.weight = kg; }

  /** Store mount'unda çağrılır. iOS'ta izin yoksa sessizce dinler; veri
   *  gelmezse needsGesture=true olur ve UI etkinleştirme butonu gösterir. */
  autoStart() {
    const DME = (window as unknown as { DeviceMotionEvent?: DMConstructor }).DeviceMotionEvent;
    if (!DME) { this.patch({ supported: false, permission: 'unsupported' }); this.notify(); return; }
    const needsGesture = typeof DME.requestPermission === 'function';
    this.patch({ supported: true, needsGesture });
    this.start();
  }

  /** Kullanıcı dokunuşuyla (iOS zorunluluğu) izin iste + başlat. */
  async requestAndStart(): Promise<void> {
    const DME = (window as unknown as { DeviceMotionEvent?: DMConstructor }).DeviceMotionEvent;
    if (!DME) { this.patch({ supported: false, permission: 'unsupported' }); this.notify(); return; }
    this.patch({ supported: true, needsGesture: typeof DME.requestPermission === 'function' });
    if (typeof DME.requestPermission === 'function') {
      try {
        const res = await DME.requestPermission();
        this.patch({ permission: res === 'granted' ? 'granted' : 'denied' });
        if (res !== 'granted') { this.notify(); return; }
      } catch {
        this.patch({ permission: 'denied' }); this.notify(); return;
      }
    } else {
      this.patch({ permission: 'granted' });
    }
    this.start();
    this.notify();
  }

  start() {
    if (this.snap.active) return;
    window.addEventListener('devicemotion', this.onMotion as EventListener, { passive: true });
    document.addEventListener('visibilitychange', this.onVisibility);
    this.notifyTimer = window.setInterval(() => {
      const now = Date.now();
      if (this.dirty) { this.dirty = false; this.notify(); }
      // uzun sessizlik: yürüyüş durumunu kapat, adayları at, idle'a geç
      if (this.lastCandAt && now - this.lastCandAt > WALK_TIMEOUT_MS) {
        if (this.walking || this.pend.length) {
          this.walking = false; this.pend = []; this.patch({ pending: 0 });
          this.notify();
        }
      }
      if (this.snap.sensorLive && now - this.lastCandAt > IDLE_MS && this.snap.mode !== 'idle') {
        this.patch({ mode: 'idle', cadence: 0 });
        this.notify();
      }
    }, NOTIFY_MS);
    this.patch({ active: true });
    this.notify();
  }

  stop() {
    if (!this.snap.active) return;
    window.removeEventListener('devicemotion', this.onMotion as EventListener);
    document.removeEventListener('visibilitychange', this.onVisibility);
    if (this.notifyTimer != null) { window.clearInterval(this.notifyTimer); this.notifyTimer = null; }
    this.patch({ active: false, mode: 'idle', cadence: 0, pending: 0 });
    this.notify();
  }

  private onVisibility = () => {
    // Arka planda pil tasarrufu: dinlemeyi duraklat, dönünce sürdür.
    if (document.hidden) {
      window.removeEventListener('devicemotion', this.onMotion as EventListener);
    } else if (this.snap.active) {
      window.addEventListener('devicemotion', this.onMotion as EventListener, { passive: true });
    }
  };

  private onMotion = (e: Event) => {
    const ev = e as unknown as DMEvent;
    const a = ev.accelerationIncludingGravity;
    if (!a || a.x == null || a.y == null || a.z == null) return;
    this.process(a.x, a.y, a.z, Date.now());
  };

  /** Sinyal işleme hattı. onMotion buraya bağlanır; test kancası da
   *  sentetik örnekleri doğrudan buraya besler.
   *
   *  Mimari not: sinyal SKALER büyüklükten (hypot - taban) çıkarılır;
   *  hypot yüksek geçirildikten sonra alınırsa işaretli sinyal yeniden
   *  doğrultulur ve tepe genliği yarıya iner (testlerde yakalanan hata).
   *  Eksen-başına yerçekimi vektörü YALNIZCA dönüş tespiti içindir. */
  process(ax: number, ay: number, az: number, now: number) {
    // 0) darbe/çarpma örneği — tamamen yut
    const mag = Math.hypot(ax, ay, az);
    if (mag > G_LIMIT) return;

    // 1) yerçekimi vektörü — dönüş tespiti İÇİN (yavaş takip, step frekansını izlemez)
    const gn0 = Math.hypot(this.gx, this.gy, this.gz) || 1;
    const ux0 = this.gx / gn0, uy0 = this.gy / gn0, uz0 = this.gz / gn0;
    const gaLive = this.rotFastUntil > now ? 0.12 : GA;
    this.gx += gaLive * (ax - this.gx);
    this.gy += gaLive * (ay - this.gy);
    this.gz += gaLive * (az - this.gz);
    const gn = Math.hypot(this.gx, this.gy, this.gz) || 1;
    const ux = this.gx / gn, uy = this.gy / gn, uz = this.gz / gn;

    // Hızlı yerçekimi takibi dönüş algılamasın diye önceki vektörü kullan.
    // Kısa pencere (baseUnit) — 250ms'de bir güncellenen yavaş referansa göre
    // mevcut yönün 8°'den fazla sapması = dönüş (kümülatif değil, anlık hareket).
    if (now - this.baseUnitAt > 250) {
      this.baseUnitAt = now;
      this.baseUnitX = ux0; this.baseUnitY = uy0; this.baseUnitZ = uz0;
    }
    const dbx = this.gx, dby = this.gy, dbz = this.gz;
    const dgn = Math.hypot(this.gx, this.gy, this.gz) || 1;
    void dbx; void dby; void dbz; void dgn;
    const dotRot = ux * this.baseUnitX + uy * this.baseUnitY + uz * this.baseUnitZ;
    if (dotRot < ROT_DOT_MIN) {
      // yönelim değişti (telefon döndü) — tespiti duraklat, adayları at,
      // takibi hızlandır ve referansı hemen yeni yöne oturt.
      this.rotUntil = now + ROT_PAUSE_MS;
      this.rotFastUntil = now + ROT_FAST_MS;
      this.baseUnitAt = now + 250;
      this.baseUnitX = ux; this.baseUnitY = uy; this.baseUnitZ = uz;
      this.walking = false;
      this.pend = [];
      this.patch({ pending: 0 });
    }
    this.pux = ux; this.puy = uy; this.puz = uz;

    // 2) yerçekimi eksenine işaretli projeksiyon: adım ivmesini tam genliğiyle
    //    taşır ve telafon döndüğünde genlik ikinci dereceye düşmez (skaler norm
    //    dönüşte sinyali 2.2→0.24 m/s²'ye sıkıştırıyordu).
    const lin = ax * ux + ay * uy + az * uz;
    if (!this.hasBase) { this.base = lin; this.hasBase = true; }
    this.base += B_ALPHA * (lin - this.base);
    this.s += S_ALPHA * ((lin - this.base) - this.s);

    // ölçülen örnekleme hızı
    if (this.lastEvtAt) {
      const dt = now - this.lastEvtAt;
      if (dt > 0 && dt < 500) {
        const hz = 1000 / dt;
        this.patch({ sensorHz: this.snap.sensorHz ? this.snap.sensorHz * 0.9 + hz * 0.1 : hz });
      }
    }
    this.lastEvtAt = now;
    if (!this.snap.sensorLive) this.patch({ sensorLive: true });

    // 3) adaptif pencere istatistikleri
    this.buf.push(this.s);
    this.sum += this.s;
    this.sumSq += this.s * this.s;
    if (this.buf.length > WINDOW) {
      const old = this.buf.shift() as number;
      this.sum -= old;
      this.sumSq -= old * old;
    }
    const n = this.buf.length;
    if (n < WARMUP) return;
    const mean = this.sum / n;
    const std = Math.sqrt(Math.max(0, this.sumSq / n - mean * mean));

    // 4) tepe tespiti (histerezisli) — ADAY üretir, saymaz
    if (now < this.rotUntil) { this.armed = false; return; }
    const thr = mean + Math.max(MIN_AMP, K_SIGMA * std);
    if (!this.armed && this.s > thr) {
      this.armed = true;
      this.candPeak = this.s;
    } else if (this.armed) {
      if (this.s > this.candPeak) this.candPeak = this.s;
      if (this.s < mean) {
        this.armed = false; // tepe bitti
        const gap = this.lastCandAt ? now - this.lastCandAt : Infinity;
        const minInt = this.snap.cadence > 140 ? MIN_INTERVAL_RUN_MS : MIN_INTERVAL_MS;
        if (this.candPeak >= thr && gap >= minInt) {
          this.finalizeCandidate(now, this.candPeak, gap);
        }
      }
    }
    this.dirty = true;
  }

  /* ---- aday → doğrulanmış adım hattı ---- */
  private finalizeCandidate(now: number, peak: number, gap: number) {
    this.lastCandAt = now;
    if (gap > MAX_INTERVAL_MS) {
      // zincir bozuldu: izole olay veya yürüyüş sonu — eski adaylar sayılmaz
      this.walking = false;
      this.pend = [{ t: now, amp: peak }];
    } else {
      this.pend.push({ t: now, amp: peak });
    }
    this.patch({ peakSigma: peak, pending: this.pend.length });
    if (!this.walking) {
      if (this.pend.length >= CONFIRM_N && now - this.pend[0].t <= CONFIRM_WINDOW_MS) {
        if (this.validatePattern()) {
          this.walking = true;
          this.confirmPending();
        } else {
          this.pend.shift(); // kayan pencere
          this.patch({ pending: this.pend.length });
        }
      }
      // henüz doğrulanamadı → beklemeye devam (izoleysen atılacaksın)
    } else {
      // yürüyüş onaylı: kadans bandı kapısı — son aralıkların medyanına göre
      // gap %55-160 içinde olmalı (kadans kaymasına izin ver, kaotik atlayışı
      // reddet). Tutarlılık bozulduysa zinciri kır ve bu adayı SAYMA.
      const recent = this.intervals.slice(-4);
      if (recent.length >= 3 && gap >= MIN_INTERVAL_MS) {
        const med = this.medianOf(recent);
        const ratio = gap / med;
        if (ratio < 0.7 || ratio > 1.35) {
          this.walking = false;
          this.intervals = [];
          this.walkingAmps = [];
          this.pend = [{ t: now, amp: peak }];
          this.patch({ pending: 1 });
          return;
        }
      }
      if (this.intervals.length >= 4 && this.walkingAmps.length >= 4) {
        const gm = this.intervals.reduce((a, b) => a + b, 0) / this.intervals.length;
        const gv = this.intervals.reduce((a, b) => a + (b - gm) * (b - gm), 0) / this.intervals.length;
        const am = this.walkingAmps.reduce((a, b) => a + b, 0) / this.walkingAmps.length;
        const av = this.walkingAmps.reduce((a, b) => a + (b - am) * (b - am), 0) / this.walkingAmps.length;
        const stepJump = Math.max(peak, this.walkingAmps[this.walkingAmps.length - 1]) /
          Math.max(1e-6, Math.min(peak, this.walkingAmps[this.walkingAmps.length - 1]));
        const broken = Math.sqrt(gv) / gm > 0.28 || Math.sqrt(av) / am > 0.28 ||
          stepJump > 1.6 || gm > MAX_INTERVAL_MS;
        if (broken) {
          this.walking = false;
          this.intervals = [];
          this.walkingAmps = [];
          this.pend = [{ t: now, amp: peak }];
          this.patch({ pending: 1 });
          return;
        }
      }
      this.walkingAmps.push(peak);
      if (this.walkingAmps.length > 5) this.walkingAmps.shift();
      this.registerMetrics(1, gap, peak);
    }
  }

  private medianOf(arr: number[]): number {
    const s = [...arr].sort((a, b) => a - b);
    const m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }

  private validatePattern(): boolean {
    const p = this.pend;
    if (p.length < CONFIRM_N) return false;
    const matchWindow = Math.min(this.pend.length, CONFIRM_N);
    const gaps: number[] = [];
    for (let i = 1; i < matchWindow; i++) gaps.push(p[i].t - p[i - 1].t);
    const mean = gaps.reduce((a, b) => a + b, 0) / gaps.length;
    if (mean < MIN_INTERVAL_MS || mean > MAX_INTERVAL_MS) return false;
    const varr = gaps.reduce((a, b) => a + (b - mean) * (b - mean), 0) / gaps.length;
    if (Math.sqrt(varr) / mean > INTERVAL_CV_MAX) return false;
    // ardışık gap oranı: gerçek yürüyüşte birbirine çok yakın olmalı
    for (let i = 1; i < gaps.length; i++) {
      const r = Math.max(gaps[i], gaps[i - 1]) / Math.min(gaps[i], gaps[i - 1]);
      if (r > 1.3) return false;
    }
    const amps = p.map((c) => c.amp);
    const peak = Math.max(...amps);
    if (peak / Math.max(1e-6, Math.min(...amps)) > AMP_RATIO_MAX) return false;
    return true;
  }

  private confirmPending() {
    const n = this.pend.length;
    if (n === 0) return;
    let avgGap = 0;
    for (let i = 1; i < n; i++) avgGap += this.pend[i].t - this.pend[i - 1].t;
    avgGap = n > 1 ? avgGap / (n - 1) : 500;
    this.walkingAmps = this.pend.map((c) => c.amp);
    this.registerMetrics(n, avgGap, this.pend[n - 1].amp);
    this.pend = [];
    this.patch({ pending: 0 });
  }

  /** Sayılan adımların kadans / mod / mesafe / kalori güncellemesi. */
  private registerMetrics(count: number, gapMs: number, peak: number) {
    if (gapMs > 150 && gapMs < 2000) {
      this.intervals.push(gapMs);
      if (this.intervals.length > 6) this.intervals.shift();
      const avg = this.intervals.reduce((x, y) => x + y, 0) / this.intervals.length;
      const inst = Math.min(230, Math.max(50, 60000 / avg));
      const smoothed = this.snap.cadence ? this.snap.cadence * 0.65 + inst * 0.35 : inst;
      const running = smoothed >= CADENCE_RUN || (smoothed >= 130 && peak >= RUN_AMP);
      const mode: PedometerMode = running ? 'running' : 'walking';
      const stride = running
        ? Math.min(1.6, Math.max(0.9, 1.05 + (smoothed - 150) * 0.004))
        : Math.min(0.9, Math.max(0.55, 0.715 + (smoothed - 100) * 0.0012));
      const met = running ? 9.8 : 3.3;
      const kcal = this.snap.kcal + ((met * 3.5 * this.weight) / 200) * (gapMs / 60000) * count;
      this.patch({
        cadence: smoothed,
        mode,
        strideM: stride,
        distanceM: this.snap.distanceM + stride * count,
        kcal,
      });
    } else {
      this.patch({ mode: 'walking', strideM: 0.72 });
    }
    this.patch({ steps: this.snap.steps + count });
    if (this.sink) this.sink(count);
  }
}

/** Uygulama genelinde tek motor. */
export const pedometer = new PedometerEngine();

/** Canlı pedometre telemetrisi için React hook'u. */
export function usePedometer(): PedometerTelemetry {
  return useSyncExternalStore(pedometer.subscribe, pedometer.getSnapshot, pedometer.getSnapshot);
}


