import { useState } from 'react';
import {
  Activity, BedDouble, Camera, Check, ChevronRight, Droplets, Dumbbell,
  Flame, Footprints, LineChart, Minus, MoonStar, Plus, Sparkles, TrendingDown, UtensilsCrossed, Zap,
} from 'lucide-react';
import { DayNavigator, Empty, HBar, Ring, SectionHead } from './chrome';
import { pedometer, usePedometer } from '../lib/pedometer';
import type { Store } from '../lib/store';
import { formatMemberSince, isToday, stepsToKcal, stepsToKm, todayISO } from '../lib/utils';
import type { TabKey } from '../lib/types';

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <section className={`card-paper rounded-3xl p-5 ${className}`}>{children}</section>;
}

/* --- gerçek adım sensörü durum göstergeleri --- */
function SensorBadge() {
  const t = usePedometer();
  if (!t.supported) return <span className="rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-extrabold text-white/50">SENSÖR YOK</span>;
  if (t.permission === 'denied') return <span className="rounded-full bg-[#fde1df] px-2.5 py-1 text-[10px] font-extrabold text-[#8f1826]">İZİN REDDİ</span>;
  if (t.active && t.sensorLive) {
    if (t.pending > 0) {
      return <span className="flex items-center gap-1.5 rounded-full bg-[#fdf3e0] px-2.5 py-1 text-[10px] font-extrabold text-[#b97a1a]"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#b97a1a]" /> DESEN DOĞRULANIYOR</span>;
    }
    return (
      <span className="flex items-center gap-1.5 rounded-full bg-[#e8f6ee] px-2.5 py-1 text-[10px] font-extrabold text-[#2e9e5b]">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#2e9e5b]" /> SENSÖR CANLI
      </span>
    );
  }
  if (t.active) return <span className="rounded-full bg-[#fdf3e0] px-2.5 py-1 text-[10px] font-extrabold text-[#b97a1a]">BAĞLANIYOR…</span>;
  return <span className="rounded-full bg-[#fdf3e0] px-2.5 py-1 text-[10px] font-extrabold text-[#b97a1a]">İZİN BEKLİYOR</span>;
}

function SensorBody() {
  const t = usePedometer();
  if (!t.supported) {
    return <p className="mt-3 rounded-xl bg-white/10 px-3 py-2 text-center text-[10px] font-bold text-white/50">Bu cihazda hareket sensörü bulunamadı — adım sayacı pasif.</p>;
  }
  const needPerm = t.needsGesture && t.permission !== 'granted' && t.permission !== 'denied';
  return (
    <>
      {needPerm && (
        <button onClick={() => { void pedometer.requestAndStart(); }} className="ember-btn mt-3 flex w-full items-center justify-center gap-2 rounded-xl py-3 text-xs font-extrabold">
          <Activity size={15} /> Adım sensörünü etkinleştir
        </button>
      )}
      {t.permission === 'denied' && (
        <p className="mt-3 rounded-xl bg-white/10 px-3 py-2 text-center text-[10px] font-bold text-white/60">Hareket izni reddedildi — cihaz ayarlarından ivmeölçer erişimini açıp uygulamayı yenile.</p>
      )}
      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        {[
          ['Tempo', t.sensorLive ? `${Math.round(t.cadence)} adım/dk` : '—'],
          ['Mod', t.mode === 'running' ? 'Koşu' : t.mode === 'walking' ? 'Yürüme' : 'Beklemede'],
          ['Oturum', `${t.steps} adım`],
        ].map(([k, val]) => (
          <div key={k} className="rounded-xl bg-white/8 px-2 py-2">
            <p className="text-[9px] font-extrabold uppercase tracking-widest text-white/50">{k}</p>
            <p className="mt-0.5 text-[13px] font-extrabold">{val}</p>
          </div>
        ))}
      </div>
      {t.sensorLive && (
        <p className="mt-2 text-center text-[10px] font-bold text-white/40">Gerçek zamanlı ivmeölçer · {Math.round(t.sensorHz)} Hz · adım uzunluğu {t.strideM.toFixed(2)} m{t.pending ? ` · ${t.pending} aday beklemede` : ''}</p>
      )}
    </>
  );
}

/* --- Ana sayfa (Akış) için kompakt canlı sensör şeridi --- */
function SensorStrip() {
  const t = usePedometer();
  if (!t.supported) return null;
  const needPerm = t.needsGesture && t.permission !== 'granted' && t.permission !== 'denied';
  if (needPerm) {
    return (
      <button onClick={() => { void pedometer.requestAndStart(); }} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-[#1c1512] py-2.5 text-xs font-extrabold text-white transition active:scale-[0.98]">
        <Activity size={14} /> Gerçek adım sensörünü etkinleştir
      </button>
    );
  }
  if (t.permission === 'denied') {
    return <p className="mt-3 text-center text-[10px] font-bold text-[#b3a696]">Hareket izni reddedildi — cihaz ayarlarından ivmeölçer erişimini açabilirsin.</p>;
  }
  return (
    <div className="mt-3 flex items-center justify-between gap-2 rounded-xl bg-[#f8f4ec] px-3.5 py-2.5">
      <span className="flex items-center gap-1.5 text-[11px] font-extrabold text-[#6f6259]">
        <span className={`h-1.5 w-1.5 rounded-full ${t.sensorLive && t.mode !== 'idle' ? 'animate-pulse bg-[#2e9e5b]' : 'bg-[#b3a696]'}`} />
        {t.sensorLive ? (t.mode === 'running' ? 'Koşuyorsun' : t.mode === 'walking' ? 'Yürüyorsun' : 'Sensör hazır') : 'Sensör bağlanıyor…'}
      </span>
      <span className="text-[11px] font-extrabold text-[#1c1512]">{t.sensorLive ? `${Math.round(t.cadence)} adım/dk · oturum ${t.steps}` : '—'}</span>
    </div>
  );
}

export function VitalityPanel({ store, iso, compact = false }: { store: Store; iso: string; compact?: boolean }) {
  const v = store.vitalsFor(iso);
  const editable = isToday(iso);
  const [waterDraft, setWaterDraft] = useState('');
  const waterPct = Math.min(100, (v.waterMl / 2500) * 100);
  const sleepPct = Math.min(100, (v.sleepHours / 8) * 100);
  const commitWater = (val: number) => {
    if (!editable) return;
    store.updateVitals(iso, { waterMl: Math.max(0, Math.min(8000, Math.round(val))) });
    setWaterDraft('');
  };
  return (
    <Card className="overflow-hidden">
      <SectionHead
        kicker={editable ? 'Günlük durum · canlı' : 'Günlük durum'}
        title="Adım · Su · Uyku"
        right={editable ? <SensorBadge /> : undefined}
      />
      {/* STEPS — gerçek ivmeölçer sensörü */}
      <div className="rounded-2xl bg-[#1c1512] p-4 text-white">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <span className="ember-btn grid h-10 w-10 place-items-center rounded-xl"><Footprints size={19} /></span>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-widest text-white/60">Adım sayar · ivmeölçer</p>
              <p className="font-display text-[26px] font-extrabold leading-none">{v.steps.toLocaleString('tr-TR')} <span className="text-xs font-bold text-white/50">adım</span></p>
            </div>
          </div>
          {editable && <Activity size={18} className="animate-pulse text-[#ff5a63]" />}
        </div>
        <div className="mt-3 flex gap-2 text-center">
          {[['Mesafe', `${stepsToKm(v.steps).toFixed(2)} km`], ['Yakılan', `${Math.round(stepsToKcal(v.steps))} kcal`], ['Hedef', '10.000']].map(([k, val]) => (
            <div key={k} className="flex-1 rounded-xl bg-white/8 px-2 py-2">
              <p className="text-[9px] font-extrabold uppercase tracking-widest text-white/50">{k}</p>
              <p className="mt-0.5 text-[13px] font-extrabold">{val}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/12">
          <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(100, (v.steps / 10000) * 100)}%`, background: 'linear-gradient(90deg,#ff5a63,#ff8a7a)' }} />
        </div>
        {editable && <SensorBody />}
        {!editable && <p className="mt-2 text-center text-[10px] font-bold text-white/40">Geçmiş gün · sensör kaydı sabitlendi</p>}
      </div>
      {/* WATER */}
      <div className="mt-3 rounded-2xl border border-[#e7ddcf] bg-white/70 p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#dbeafe] text-[#2563eb]"><Droplets size={19} /></span>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-widest text-[#9a8c80]">Su · girişi sen yap</p>
              <p className="font-display text-xl font-extrabold leading-none text-[#1c1512]">{v.waterMl.toLocaleString('tr-TR')} <span className="text-xs font-bold text-[#9a8c80]">/ 2.500 ml</span></p>
            </div>
          </div>
        </div>
        <div className="mt-3"><HBar pct={waterPct} tone="ink" /></div>
        {editable ? (
          <div className="mt-3 flex items-center gap-2">
            <button onClick={() => commitWater(v.waterMl - 250)} className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-[#e2d7c6] bg-white transition active:scale-90" aria-label="250 ml azalt"><Minus size={17} /></button>
            <button onClick={() => commitWater(v.waterMl + 250)} className="grid h-11 flex-1 place-items-center gap-1 rounded-xl bg-[#2563eb] py-3 text-sm font-extrabold text-white transition active:scale-[0.98]" ><span className="flex items-center gap-1.5"><Plus size={16} /> +250 ml bardak</span></button>
            <button onClick={() => commitWater(v.waterMl + 500)} className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-[#e2d7c6] bg-white text-xs font-extrabold transition active:scale-90">+500</button>
          </div>
        ) : null}
        {editable && (
          <form className="mt-2 flex gap-2" onSubmit={(e) => { e.preventDefault(); const n = parseInt(waterDraft, 10); if (!Number.isNaN(n)) commitWater(v.waterMl + n); }}>
            <input value={waterDraft} onChange={(e) => setWaterDraft(e.target.value)} inputMode="numeric" placeholder="ml yaz (örn. 300)" className="h-11 min-w-0 flex-1 rounded-xl border border-[#e2d7c6] bg-white px-3 text-sm font-bold outline-none placeholder:font-medium placeholder:text-[#b3a696] focus:border-[#2563eb]" />
            <button type="submit" className="h-11 shrink-0 rounded-xl bg-[#1c1512] px-4 text-sm font-extrabold text-white active:scale-95">Ekle</button>
          </form>
        )}
      </div>
      {/* SLEEP — sabah check-in'inden beslenir, burada salt-okunur */}
      <div className="mt-3 rounded-2xl border border-[#e7ddcf] bg-white/70 p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#ede9fe] text-[#7c3aed]"><BedDouble size={19} /></span>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-widest text-[#9a8c80]">Uyku · günlük check-in</p>
              <p className="font-display text-xl font-extrabold leading-none text-[#1c1512]">{v.sleepHours > 0 ? `${v.sleepHours} saat` : '—'} <span className="text-xs font-bold text-[#9a8c80]">/ 8 saat</span></p>
            </div>
          </div>
          {v.sleepQuality ? (
            <span className="flex items-center gap-1 rounded-full bg-[#ede9fe] px-2.5 py-1 text-[10px] font-extrabold text-[#7c3aed]"><MoonStar size={12} /> {v.sleepQuality}/5</span>
          ) : (
            <span className="rounded-full bg-[#f1ece2] px-2.5 py-1 text-[10px] font-extrabold text-[#9a8c80]">bekliyor</span>
          )}
        </div>
        <div className="mt-3"><HBar pct={sleepPct} tone="amber" /></div>
        {editable && v.sleepHours === 0 ? (
          <p className="mt-2 text-center text-[11px] font-semibold text-[#9a8c80]">Bugünkü uykun günlük check-in'den gelir — üstteki karttan doldurabilirsin.</p>
        ) : !editable && v.sleepHours === 0 ? (
          <p className="mt-2 text-center text-[11px] font-semibold text-[#9a8c80]">Bu güne uyku kaydı yok</p>
        ) : null}
      </div>
    </Card>
  );
}

export function FlowScreen({ store, go, onOpenCheckIn }: { store: Store; go: (t: TabKey) => void; onOpenCheckIn?: () => void }) {
  const t = todayISO();
  const v = store.vitalsFor(t);
  const meals = store.mealsFor(t);
  const cal = meals.reduce((s, m) => s + m.calories, 0);
  const prot = meals.reduce((s, m) => s + m.protein, 0);
  const prog = store.programFor(t);
  const doneCount = prog ? prog.exercises.filter((e) => store.doneMap[t]?.[e.name]).length : 0;
  const totalSets = prog ? prog.exercises.reduce((s, e) => s + e.sets, 0) : 0;
  const first = store.profile.name.split(' ')[0] || 'Sporcu';
  const hour = new Date().getHours();
  const greet = hour < 6 ? 'İyi geceler' : hour < 12 ? 'Günaydın' : hour < 18 ? 'İyi günler' : 'İyi akşamlar';
  return (
    <div>
      <div className="rise-in flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="eyebrow text-[#d92835]">{greet}, {first} · {store.profile.streak} günlük seri</p>
          <h1 className="font-display mt-1.5 text-[30px] font-extrabold leading-[1.05]">Bugünün<br />akışı<span className="text-[#d92835]">.</span></h1>
        </div>
        <button onClick={() => go('coach')} className="ember-btn flex shrink-0 items-center gap-1.5 rounded-full px-4 py-2.5 text-xs font-extrabold">
          <Sparkles size={14} /> Koça sor
        </button>
      </div>
      {/* HERO */}
      <section className="rise-in stagger-1 relative mt-4 overflow-hidden rounded-[28px] bg-[#1c1512] p-6 text-white grain">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-[#d92835]/40 blur-[70px]" />
          <div className="absolute -bottom-20 -left-10 h-48 w-48 rounded-full bg-[#c99a3f]/25 blur-[70px]" />
          <div className="absolute right-8 top-1/2 h-40 w-40 -translate-y-1/2 rounded-full border-[22px] border-white/8" />
        </div>
        <div className="relative">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="eyebrow text-[#ff8a7a]">Bugünün odağı</p>
              <h2 className="font-display mt-1.5 text-[24px] font-extrabold leading-tight">{prog ? prog.focus : 'Dinlenme'}</h2>
              <p className="mt-1 text-[13px] font-medium text-white/60">{prog ? `${prog.exercises.length} hareket · ${prog.duration} · ${totalSets} set` : 'Toparlan, yarın devam.'}</p>
            </div>
            <span className="ember-btn grid h-13 w-13 shrink-0 place-items-center rounded-2xl p-3.5"><Dumbbell size={24} /></span>
          </div>
          <div className="mt-5 flex items-center gap-3">
            <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-white/12">
              <div className="h-full rounded-full transition-all duration-700" style={{ width: `${prog ? (doneCount / Math.max(1, prog.exercises.length)) * 100 : 0}%`, background: 'linear-gradient(90deg,#ff5a63,#ffb199)' }} />
            </div>
            <span className="text-xs font-extrabold text-white/80">{doneCount}/{prog?.exercises.length ?? 0}</span>
          </div>
          <button onClick={() => go('workout')} className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-2xl bg-white py-3.5 text-sm font-extrabold text-[#1c1512] transition active:scale-[0.98]">
            {prog ? 'Antrenmanı aç' : 'Programı gör'} <ChevronRight size={17} />
          </button>
        </div>
      </section>
      {/* PENDING CHECK-IN — günün check-in'i yapılmadıysa akışta hep kart var.
          (kullanıcı yeni açtığında da otomatik sorulmasa bile tıklayıp doldurabilir) */}
      {store.checkinMap[t] !== 'done' && onOpenCheckIn && (
        <button onClick={onOpenCheckIn} className="rise-in stagger-1 mt-3 flex w-full items-center gap-3.5 rounded-3xl border border-[#e7ddcf] bg-white p-4 text-left transition active:scale-[0.99]">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[#ede9fe] text-[#7c3aed]"><MoonStar size={20} /></span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-extrabold text-[#1c1512]">Günlük check-in bekliyor</span>
            <span className="block text-xs font-medium text-[#9a8c80]">Uyku, enerji ve kilonla güne başla — 10 saniye sürer.</span>
          </span>
          <ChevronRight size={18} className="shrink-0 text-[#b3a696]" />
        </button>
      )}
      {/* RINGS */}
      <section className="rise-in stagger-2 card-paper mt-3 rounded-3xl p-5">
        <SectionHead kicker="Günlük durum" title="Hedeflere ilerleme" />
        <div className="grid grid-cols-3 gap-1">
          <Ring value={Math.round(cal)} target={store.profile.targets.calories} label="Kalori" unit="kcal" tone="red" />
          <Ring value={Math.round(prot)} target={store.profile.targets.protein} label="Protein" unit="g" tone="green" />
          <Ring value={v.steps} target={10000} label="Adım" unit="adım" tone="amber" />
        </div>
        <SensorStrip />
      </section>
      {/* VITALITY unified */}
      <div className="rise-in stagger-3 mt-3"><VitalityPanel store={store} iso={t} compact /></div>
      {/* COACH bridge */}
      <button onClick={() => go('coach')} className="rise-in stagger-3 mt-3 flex w-full items-center gap-3.5 overflow-hidden rounded-3xl bg-gradient-to-br from-[#2a1215] via-[#1c1512] to-[#3a1c22] p-5 text-left text-white grain transition active:scale-[0.99]">
        <span className="ember-btn grid h-12 w-12 shrink-0 place-items-center rounded-2xl"><Sparkles size={22} /></span>
        <span className="min-w-0 flex-1">
          <span className="block text-[15px] font-extrabold">Lumiere yanında</span>
          <span className="block truncate text-xs font-medium text-white/60">Bugün nasıl hissediyorsun? Yaz, planı uyarlayayım.</span>
        </span>
        <ChevronRight size={18} className="shrink-0 text-white/50" />
      </button>
      {/* quick actions */}
      <div className="rise-in stagger-4 mt-3 grid grid-cols-2 gap-3">
        <button onClick={() => go('nutrition')} className="card-paper rounded-3xl p-4 text-left transition active:scale-[0.98]">
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-[#fde1df] text-[#d92835]"><Flame size={20} /></span>
          <p className="mt-3 text-sm font-extrabold text-[#1c1512]">Öğün ekle</p>
          <p className="text-xs font-semibold text-[#9a8c80]">{Math.round(cal)} / {store.profile.targets.calories} kcal</p>
        </button>
        <button onClick={() => go('nutrition')} className="card-paper rounded-3xl p-4 text-left transition active:scale-[0.98]">
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-[#e8f6ee] text-[#2e9e5b]"><Camera size={20} /></span>
          <p className="mt-3 text-sm font-extrabold text-[#1c1512]">Foto analizi</p>
          <p className="text-xs font-semibold text-[#9a8c80]">Makroları otomatik bul</p>
        </button>
      </div>
      {/* weight bridge */}
      <section className="rise-in stagger-5 card-paper mt-3 rounded-3xl p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="eyebrow text-[#b3a696]">Kilo değişimi</p>
            <p className="font-display mt-1 text-[26px] font-extrabold text-[#1c1512]">{store.profile.currentWeight} kg</p>
          </div>
          <span className="flex items-center gap-1 rounded-full bg-[#e8f6ee] px-3 py-1.5 text-xs font-extrabold text-[#2e9e5b]"><TrendingDown size={14} /> Hedef {store.profile.targetWeight} kg</span>
        </div>
        <button onClick={() => go('progress')} className="mt-4 flex w-full items-center justify-between rounded-2xl border border-[#e7ddcf] bg-white px-4 py-3.5 text-sm font-extrabold text-[#1c1512] transition active:scale-[0.99]">
          <span className="flex items-center gap-2"><LineChart size={17} className="text-[#d92835]" /> Grafiklerini gör</span>
          <ChevronRight size={17} className="text-[#9a8c80]" />
        </button>
      </section>
      {/* membership */}
      <section className="card-paper mt-3 rounded-3xl p-5">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="eyebrow text-[#b3a696]">Üyelik</p>
            <p className="mt-1 truncate text-sm font-extrabold text-[#1c1512]">{formatMemberSince(store.profile.memberSince) ?? 'Lumiere üyesi'}</p>
            <p className="mt-0.5 flex items-center gap-1 text-xs font-semibold text-[#9a8c80]"><Zap size={12} className="text-[#c99a3f]" /> {store.profile.goal} · {store.profile.level}</p>
          </div>
          <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-[#1c1512] px-3 py-1.5 text-[11px] font-extrabold text-white"><UtensilsCrossed size={12} /> PRO</span>
        </div>
      </section>
    </div>
  );
}

export function DailyScreen({ store }: { store: Store }) {
  const iso = store.selectedDate;
  const rec = store.dayRecord(iso);
  const cal = rec.meals.reduce((s, m) => s + m.calories, 0);
  const prot = rec.meals.reduce((s, m) => s + m.protein, 0);
  const totalSets = rec.exercises.reduce((s, e) => s + e.sets.length, 0);
  const grouped = rec.exercises.reduce<Record<string, typeof rec.exercises>>((acc, e) => {
    (acc[e.muscle] = acc[e.muscle] || []).push(e);
    return acc;
  }, {});
  const heat = Object.entries(grouped)
    .map(([muscle, list]) => ({ muscle, sets: list.reduce((s, e) => s + e.sets.length, 0) }))
    .sort((a, b) => b.sets - a.sets);
  const maxHeat = heat.length ? Math.max(...heat.map((h) => h.sets), 1) : 1;
  const note = isToday(iso) ? undefined : iso > todayISO() ? 'Gelecek gün — kayıtlar boş başlar' : 'Yalnızca bu günün verileri gösteriliyor';
  return (
    <div>
      <div className="rise-in">
        <p className="eyebrow text-[#d92835]">Günlük takip</p>
        <h1 className="font-display mt-1.5 text-[30px] font-extrabold leading-tight">Seçili gün<span className="text-[#d92835]">.</span></h1>
        <p className="mt-1.5 text-[13px] font-medium text-[#6f6259]">Aşağıdaki her şey yalnızca seçtiğin güne ait — başka gün karışmaz.</p>
      </div>
      <div className="rise-in stagger-1 mt-4">
        <DayNavigator iso={iso} onChange={store.setSelectedDate} onShift={store.shiftSelectedDate} note={note} />
      </div>
      <section className="rise-in stagger-2 card-paper mt-3 rounded-3xl p-5">
        <SectionHead kicker="Bu günün özeti" title={`${Math.round(cal).toLocaleString('tr-TR')} kcal · ${Math.round(prot)}g protein · ${totalSets} set`} />
        <div className="grid grid-cols-3 gap-1">
          <Ring value={Math.round(cal)} target={store.profile.targets.calories} label="Kalori" unit="kcal" tone="red" />
          <Ring value={Math.round(prot)} target={store.profile.targets.protein} label="Protein" unit="g" tone="green" />
          <Ring value={totalSets} target={20} label="Antrenman" unit="set" tone="amber" />
        </div>
      </section>
      <div className="rise-in stagger-3 mt-3"><VitalityPanel store={store} iso={iso} /></div>
      {/* meals of selected day only */}
      <Card className="rise-in stagger-4 mt-3">
        <SectionHead kicker="Öğünler · seçili gün" right={<span className="rounded-full bg-[#f1ece2] px-2.5 py-1 text-[11px] font-extrabold text-[#6f6259]">{rec.meals.length} kayıt</span>} />
        {rec.meals.length === 0 ? <Empty text={isToday(iso) ? 'Bugün henüz öğün yok — Beslenme sekmesinden ekle.' : 'Bu güne ait öğün kaydı yok.'} /> : (
          <div className="space-y-2">
            {rec.meals.map((m) => (
              <div key={m.id} className="flex items-center gap-3 rounded-2xl border border-[#ece2d2] bg-white px-3.5 py-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#fde1df] text-[#d92835]"><Flame size={15} /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-extrabold text-[#1c1512]">{m.name}</p>
                  <p className="truncate text-[11px] font-semibold text-[#9a8c80]">P {Math.round(m.protein)} · K {Math.round(m.carbs)} · Y {Math.round(m.fats)} · {m.time}</p>
                </div>
                <span className="font-display shrink-0 text-[15px] font-extrabold text-[#1c1512]">{Math.round(m.calories)}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
      {/* workout logs of selected day only */}
      <Card className="rise-in stagger-5 mt-3">
        <SectionHead kicker="Antrenman · seçili gün" right={<span className="rounded-full bg-[#f1ece2] px-2.5 py-1 text-[11px] font-extrabold text-[#6f6259]">{totalSets} set</span>} />
        {rec.exercises.length === 0 ? <Empty text={isToday(iso) ? 'Bugün henüz set kaydı yok — Antrenman sekmesinden logla.' : 'Bu güne ait antrenman kaydı yok.'} /> : (
          <div className="space-y-2">
            {rec.exercises.map((e, i) => (
              <div key={`${e.name}-${i}`} className="rounded-2xl border border-[#ece2d2] bg-white px-3.5 py-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-sm font-extrabold text-[#1c1512]">{e.name}</p>
                  <span className="shrink-0 rounded-full bg-[#1c1512] px-2 py-0.5 text-[10px] font-extrabold text-white">{e.sets.length} set</span>
                </div>
                <p className="mt-1 truncate text-[11px] font-semibold text-[#9a8c80]">{e.sets.map((s) => `${s.kg}kg×${s.reps}`).join(' · ')}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
      {heat.length > 0 && (
        <Card className="mt-3">
          <SectionHead kicker="Kas grubu yoğunluğu · seçili gün" />
          <div className="space-y-2.5">
            {heat.map((h) => (
              <div key={h.muscle}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-extrabold text-[#1c1512]">{h.muscle}</span>
                  <span className="text-[11px] font-bold text-[#9a8c80]">{h.sets} set</span>
                </div>
                <HBar pct={(h.sets / maxHeat) * 100} tone="red" />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
