// Lumiere sabah check-in'i — günün ilk açılışında uyku, uyku kalitesi,
// enerji, ruh hali ve kiloyu tek ekranda toplar. Veriler mevcut hatlara
// akar: updateVitals (uyku /api/metrics'e senkron) + logWeight (kilo).
// "Şimdi değil" seçeneği günü 'snoozed' işaretler; akışta kart kalır.
import { useState } from 'react';
import { Check, ChevronRight, MoonStar, X } from 'lucide-react';
import { Logo } from './chrome';
import { todayISO } from '../lib/utils';
import { apiFetch } from '../services/apiClient';
import type { Store } from '../lib/store';

const QUALITY_FACES = ['😫', '😕', '🙂', '😊', '🤩'];
const ENERGY_FACES = ['😵', '🥱', '🙂', '⚡', '🚀'];
const MOOD_FACES = ['😞', '😕', '🙂', '😊', '🤩'];
const SLEEP_CHIPS: Array<[string, number]> = [['<6', 5.5], ['6-7', 6.5], ['7-8', 7.5], ['8+', 8.5]];

function FaceRow({ label, value, onChange, faces }: { label: string; value: number; onChange: (n: number) => void; faces: string[] }) {
  return (
    <div>
      <p className="eyebrow text-[#b3a696]">{label}</p>
      <div className="mt-2 flex gap-2">
        {faces.map((f, i) => (
          <button
            key={f}
            type="button"
            onClick={() => onChange(value === i + 1 ? 0 : i + 1)}
            className={`h-11 flex-1 rounded-xl text-xl transition active:scale-95 ${value === i + 1 ? 'bg-[#1c1512] shadow-[0_10px_22px_-10px_rgba(28,21,18,0.7)]' : 'bg-[#f1ece2] opacity-70 grayscale-[0.4]'}`}
            aria-label={`${label} ${i + 1}/5`}
          >
            {f}
          </button>
        ))}
      </div>
    </div>
  );
}

export function MorningCheckIn({ store, onDone }: { store: Store; onDone: () => void }) {
  const iso = todayISO();
  const v = store.vitalsFor(iso);
  const [sleep, setSleep] = useState(v.sleepHours > 0 ? v.sleepHours : 7.5);
  const [quality, setQuality] = useState(v.sleepQuality ?? 0);
  const [energy, setEnergy] = useState(0);
  const [mood, setMood] = useState(0);
  const [weight, setWeight] = useState(String(store.weightMap[iso] ?? store.profile.currentWeight));
  const [saved, setSaved] = useState(false);

  const feedback = (() => {
    if (sleep >= 7 && sleep <= 9) return 'Uyku hedefinin içinde — kaslar tamiratta, metabolizma hızlı. Böyle devam!';
    if (sleep < 7) return 'Biraz kısa kalmış — bugün öğleden sonra 15-20 dakikalık kısa şekerleme iyi gelir.';
    return 'Uzun bir uyku! Hafif yorgunluk normal olabilir, gün boyunca bol su iç.';
  })();

  const save = () => {
    store.updateVitals(iso, {
      sleepHours: Math.max(0, Math.min(16, Math.round(sleep * 10) / 10)),
      ...(quality ? { sleepQuality: quality } : {}),
      ...(energy ? { energy } : {}),
      ...(mood ? { mood } : {}),
    });
    const w = parseFloat(weight.replace(',', '.'));
    if (!Number.isNaN(w) && w >= 30 && w <= 250) store.logWeight(iso, Math.round(w * 10) / 10);
    store.markCheckinDone(iso);
    // Yapılandırılmış check-in'i backend'e de işle (DailyCheckIn + hazırlık skoru).
    // Başarısızlık yerel kaydı asla engellemez — best-effort.
    void apiFetch('/api/jarvis/checkin', {
      method: 'POST',
      body: JSON.stringify({
        mood: mood || 3,
        energy: energy || 3,
        sleep_quality: quality || 3,
        soreness: 2,
        notes: `Uyku ${Math.round(sleep * 10) / 10} saat${quality ? ` · kalite ${quality}/5` : ''}`,
      }),
      timeoutMs: 60_000,
    }).catch(() => undefined);
    setSaved(true);
    window.setTimeout(onDone, 3000);
  };

  if (saved) {
    return (
      <div className="fixed inset-0 z-50">
        <div className="absolute inset-0 bg-black/45 backdrop-blur-sm" />
        <div className="rise-in absolute inset-x-0 bottom-0 mx-auto w-full max-w-md rounded-t-[28px] bg-[#f4f1ec] p-8 pb-14 text-center text-[#1c1512]">
          <span className="mx-auto grid h-16 w-16 place-items-center rounded-3xl bg-[#e8f6ee] text-[#2e9e5b]"><Check size={30} strokeWidth={3} /></span>
          <h2 className="font-display mt-4 text-2xl font-extrabold">Günlüğün alındı!</h2>
          <p className="mx-auto mt-2 max-w-xs text-sm font-medium leading-relaxed text-[#6f6259]">{feedback}</p>
          <p className="mt-3 text-xs font-bold text-[#9a8c80]">
            {sleep} saat uyku{quality ? ` · kalite ${quality}/5` : ''}{weight.trim() ? ` · ${weight.trim()} kg` : ''}
          </p>
        </div>
      </div>
    );
  }
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/45 backdrop-blur-sm" />
      <div className="rise-in absolute inset-x-0 bottom-0 mx-auto max-h-[90dvh] w-full max-w-md overflow-y-auto rounded-t-[28px] bg-[#f4f1ec] p-6 pb-10 text-[#1c1512]">
        <div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-[#ddd0bd]" />
        <div className="flex items-center justify-between">
          <Logo />
          <button onClick={onDone} aria-label="Kapat" className="grid h-10 w-10 place-items-center rounded-full border border-[#e2d7c6] bg-white"><X size={18} /></button>
        </div>
        <p className="eyebrow mt-5 text-[#d92835]">Günlük check-in</p>
        <h2 className="font-display mt-1 text-2xl font-extrabold">Güne dair 4 dokunuş</h2>

        {/* UYKU SAATİ */}
        <div className="card-paper mt-4 rounded-3xl p-5">
          <div className="flex items-center justify-between gap-2">
            <p className="eyebrow text-[#b3a696]">Dün gece kaç saat uyudun?</p>
            <span className="flex items-center gap-1 rounded-full bg-[#ede9fe] px-2.5 py-1 text-[10px] font-extrabold text-[#7c3aed]"><MoonStar size={12} /> {sleep} saat</span>
          </div>
          <div className="mt-3 grid grid-cols-4 gap-2">
            {SLEEP_CHIPS.map(([label, val]) => (
              <button key={label} type="button" onClick={() => setSleep(val)} className={`rounded-xl py-2.5 text-xs font-extrabold transition active:scale-95 ${sleep === val ? 'bg-[#7c3aed] text-white' : 'bg-[#f1ece2] text-[#6f6259]'}`}>{label}</button>
            ))}
          </div>
          <input
            type="range" min={0} max={12} step={0.5} value={sleep}
            onChange={(e) => setSleep(parseFloat(e.target.value))}
            className="lumi-range mt-3 w-full"
            style={{ ['--fill' as string]: `${(sleep / 12) * 100}%` }}
            aria-label="Uyku süresi"
          />
          <div className="mt-1 flex justify-between text-[10px] font-bold text-[#9a8c80]"><span>0s</span><span>6s</span><span>8s ideal</span><span>12s</span></div>
        </div>

        {/* KALİTE / ENERJİ / RUH HALİ */}
        <div className="card-paper mt-3 rounded-3xl p-5">
          <FaceRow label="Uyku kalitesi" value={quality} onChange={setQuality} faces={QUALITY_FACES} />
          <div className="mt-3.5"><FaceRow label="Enerjin" value={energy} onChange={setEnergy} faces={ENERGY_FACES} /></div>
          <div className="mt-3.5"><FaceRow label="Ruh halin" value={mood} onChange={setMood} faces={MOOD_FACES} /></div>
        </div>

        {/* KİLO */}
        <div className="card-paper mt-3 rounded-3xl p-5">
          <p className="eyebrow text-[#b3a696]">Bugünkü kilon</p>
          <div className="mt-2 flex items-center justify-center gap-3 rounded-2xl bg-[#f8f4ec] p-4">
            <input value={weight} onChange={(e) => setWeight(e.target.value)} inputMode="decimal" className="font-display w-28 bg-transparent text-center text-4xl font-extrabold outline-none" />
            <span className="text-base font-extrabold text-[#9a8c80]">kg</span>
          </div>
        </div>

        <button onClick={save} className="ember-btn mt-4 flex w-full items-center justify-center gap-2 rounded-2xl py-4 text-[15px] font-extrabold">
          Günümü kaydet <ChevronRight size={18} />
        </button>
        <button
          type="button"
          onClick={() => { store.snoozeCheckIn(iso); onDone(); }}
          className="mt-2.5 w-full rounded-2xl py-3 text-xs font-extrabold text-[#9a8c80] transition active:scale-[0.99]"
        >
          Şimdi değil — bugün bir daha sorma
        </button>
      </div>
    </div>
  );
}
