import { useEffect, useRef, useState } from 'react';
import { Scale, Send, Sparkles, TrendingDown, TrendingUp } from 'lucide-react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { Empty, HBar, SectionHead } from './chrome';
import type { Store } from '../lib/store';
import { shiftISO, todayISO } from '../lib/utils';

const QUICK = ['Protein hedefim?', 'Bugün ne yemeliyim?', 'Omzum ağrıyor', 'Uyku düzenim nasıl olmalı?'];

/* ================= AI COACH ================= */
export function CoachScreen({ store }: { store: Store }) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [store.chat.length, store.chatTyping]);
  const t = todayISO();
  const v = store.vitalsFor(t);
  const meals = store.mealsFor(t);
  const prot = meals.reduce((s, m) => s + m.protein, 0);
  const send = (text: string) => store.sendChat(text);
  return (
    <div className="flex min-h-[calc(100dvh-220px)] flex-col">
      {/* coach hero */}
      <section className="rise-in relative overflow-hidden rounded-[28px] bg-[#1c1512] p-6 text-white grain">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -left-14 -top-14 h-52 w-52 rounded-full bg-[#d92835]/45 blur-[70px]" />
          <div className="absolute -bottom-16 right-0 h-48 w-48 rounded-full bg-[#7c3aed]/30 blur-[70px]" />
        </div>
        <div className="relative flex items-center gap-3.5">
          <div className="relative shrink-0">
            <span className="ember-btn grid h-15 w-15 place-items-center rounded-3xl p-4"><Sparkles size={28} /></span>
            <span className="absolute -bottom-0.5 -right-0.5 h-4 w-4 rounded-full border-[3px] border-[#1c1512] bg-[#4cc38a]" />
          </div>
          <div className="min-w-0">
            <p className="eyebrow text-[#ff8a7a]">Lumiere AI Koç · çevrimiçi</p>
            <h1 className="font-display mt-1 text-[24px] font-extrabold leading-tight">Sor, uyarlayayım<span className="text-[#ff5a63]">.</span></h1>
          </div>
        </div>
        <div className="relative mt-4 grid grid-cols-3 gap-2 text-center">
          {[
            [`${v.steps.toLocaleString('tr-TR')}`, 'adım'],
            [`${Math.round(prot)}/${store.profile.targets.protein}g`, 'protein'],
            [v.sleepHours > 0 ? `${v.sleepHours}s` : '—', 'uyku'],
          ].map(([val, k]) => (
            <div key={k} className="rounded-2xl bg-white/8 px-2 py-2.5">
              <p className="text-[13px] font-extrabold">{val}</p>
              <p className="text-[9px] font-extrabold uppercase tracking-widest text-white/50">{k}</p>
            </div>
          ))}
        </div>
      </section>
      {/* messages */}
      <div className="rise-in stagger-2 mt-3 flex-1 space-y-2.5">
        {store.chat.map((m) => (
          <div key={m.id} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div className={`max-w-[86%] px-4 py-3 text-[13.5px] font-medium leading-relaxed ${m.role === 'user' ? 'rounded-2xl rounded-br-md bg-[#1c1512] text-white' : 'card-paper rounded-2xl rounded-bl-md text-[#2c231e]'}`}>
              {m.tag && <span className="eyebrow mb-1 block text-[9px] text-[#d92835]">{m.tag}</span>}
              {m.text}
              <span className={`mt-1.5 block text-right text-[10px] font-bold ${m.role === 'user' ? 'text-white/40' : 'text-[#b3a696]'}`}>{m.time}</span>
            </div>
          </div>
        ))}
        {store.chatTyping && (
          <div className="flex justify-start">
            <div className="card-paper flex items-center gap-1.5 rounded-2xl rounded-bl-md px-4 py-3.5">
              {[0, 1, 2].map((i) => (
                <span key={i} className="h-2 w-2 animate-bounce rounded-full bg-[#d92835]" style={{ animationDelay: `${i * 0.15}s` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      {/* quick + input */}
      <div className="sticky bottom-[92px] mt-3">
        <div className="no-scrollbar mb-2 flex gap-2 overflow-x-auto pb-0.5">
          {QUICK.map((q) => (
            <button key={q} onClick={() => send(q)} className="shrink-0 rounded-full border border-[#e2d7c6] bg-white px-3.5 py-2 text-xs font-extrabold text-[#6f6259] shadow-sm transition active:scale-95">{q}</button>
          ))}
        </div>
        <form
          onSubmit={(e) => { e.preventDefault(); send(store.chatInput); }}
          className="card-paper flex items-center gap-2 rounded-3xl p-2"
        >
          <input
            value={store.chatInput}
            onChange={(e) => store.setChatInput(e.target.value)}
            placeholder="Koçuna yaz… (örn. bugün ne yiyeyim?)"
            className="h-12 min-w-0 flex-1 bg-transparent px-3 text-[15px] font-medium outline-none placeholder:text-[#b3a696]"
          />
          <button type="submit" aria-label="Gönder" disabled={!store.chatInput.trim() || store.chatTyping} className="ember-btn grid h-12 w-12 shrink-0 place-items-center rounded-2xl disabled:opacity-50">
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}

/* ================= PROGRESS (charts live) ================= */
function ChartTip({ active, payload, label, suffix }: { active?: boolean; payload?: Array<{ value: number | string }>; label?: string; suffix: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-[#e7ddcf] bg-white px-3 py-2 shadow-lg">
      <p className="text-[10px] font-extrabold text-[#9a8c80]">{label}</p>
      <p className="font-display text-sm font-extrabold text-[#1c1512]">{payload[0].value} {suffix}</p>
    </div>
  );
}

export function ProgressScreen({ store }: { store: Store }) {
  const [kg, setKg] = useState('');
  const [range, setRange] = useState<7 | 14 | 30>(14);
  const t = todayISO();
  const weights = store.weightSeries.slice(-range);
  const days = store.last14.slice(-range);
  const latest = store.profile.currentWeight;
  const first = weights.length ? weights[0].weight : latest;
  const delta = Math.round((latest - first) * 10) / 10;
  const calData = days.map((d) => ({
    d: d.iso.slice(8, 10) + '/' + d.iso.slice(5, 7),
    kcal: d.meals.reduce((s, m) => s + m.calories, 0),
    hedef: store.profile.targets.calories,
  }));
  const stepData = days.map((d) => ({
    d: d.iso.slice(8, 10) + '/' + d.iso.slice(5, 7),
    adım: d.vitals.steps,
  }));
  const sleepData = days
    .filter((d) => d.vitals.sleepHours > 0)
    .map((d) => ({
      d: d.iso.slice(8, 10) + '/' + d.iso.slice(5, 7),
      saat: d.vitals.sleepHours,
    }));
  const waterData = days.map((d) => ({
    d: d.iso.slice(8, 10) + '/' + d.iso.slice(5, 7),
    ml: d.vitals.waterMl,
  }));
  const maxSteps = Math.max(1, ...stepData.map((s) => s.adım));
  const avgSteps = Math.round(stepData.reduce((s, x) => s + x.adım, 0) / Math.max(1, stepData.length));
  const avgSleep = sleepData.length ? (sleepData.reduce((s, x) => s + x.saat, 0) / sleepData.length).toFixed(1) : '—';
  const streakDays = (() => {
    let n = 0;
    for (let i = 0; i < 30; i++) {
      const iso = shiftISO(t, -i);
      const d = store.dayRecord(iso);
      if (d.meals.length || d.exercises.length || d.vitals.waterMl > 0) n++;
      else break;
    }
    return n;
  })();
  const saveWeight = (e: React.FormEvent) => {
    e.preventDefault();
    const n = parseFloat(kg.replace(',', '.'));
    if (Number.isNaN(n) || n < 30 || n > 250) return;
    store.logWeight(t, Math.round(n * 10) / 10);
    setKg('');
  };
  return (
    <div>
      <div className="rise-in">
        <p className="eyebrow text-[#d92835]">Gelişim takibi</p>
        <h1 className="font-display mt-1.5 text-[30px] font-extrabold leading-tight">İlerlemen<span className="text-[#d92835]">.</span></h1>
      </div>
      {/* range */}
      <div className="rise-in stagger-1 mt-4 grid grid-cols-3 gap-1.5 rounded-2xl border border-[#e7ddcf] bg-white p-1.5">
        {([7, 14, 30] as const).map((r) => (
          <button key={r} onClick={() => setRange(r)} className={`rounded-xl py-2 text-xs font-extrabold transition ${range === r ? 'bg-[#1c1512] text-white' : 'text-[#9a8c80]'}`}>
            {r === 30 ? '30 gün' : `${r} gün`}
          </button>
        ))}
      </div>
      {/* KPI row */}
      <div className="rise-in stagger-1 mt-3 grid grid-cols-3 gap-2">
        {[
          { k: 'Seri', v: `${streakDays} gün`, tone: 'text-[#d92835] bg-[#fde1df]' },
          { k: 'Ort. adım', v: avgSteps.toLocaleString('tr-TR'), tone: 'text-[#b97a1a] bg-[#fdf3e0]' },
          { k: 'Ort. uyku', v: `${avgSleep}s`, tone: 'text-[#7c3aed] bg-[#ede9fe]' },
        ].map((s) => (
          <div key={s.k} className="card-paper rounded-2xl p-3 text-center">
            <p className={`mx-auto w-fit rounded-full px-2 py-0.5 text-[9px] font-extrabold uppercase tracking-widest ${s.tone}`}>{s.k}</p>
            <p className="font-display mt-1.5 text-[17px] font-extrabold text-[#1c1512]">{s.v}</p>
          </div>
        ))}
      </div>
      {/* weight card + entry */}
      <section className="rise-in stagger-2 card-paper mt-3 rounded-3xl p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="eyebrow text-[#b3a696]">Güncel kilo</p>
            <p className="font-display mt-1 text-[32px] font-extrabold leading-none text-[#1c1512]">{latest} <span className="text-base font-bold text-[#9a8c80]">kg</span></p>
            <p className={`mt-2 flex items-center gap-1 text-xs font-extrabold ${delta <= 0 ? 'text-[#2e9e5b]' : 'text-[#b97a1a]'}`}>
              {delta <= 0 ? <TrendingDown size={14} /> : <TrendingUp size={14} />}
              Başlangıçtan {delta > 0 ? '+' : ''}{delta.toFixed(1)} kg · hedef {store.profile.targetWeight} kg
            </p>
          </div>
          <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#f1ece2] text-[#6f6259]"><Scale size={22} /></span>
        </div>
        <form onSubmit={saveWeight} className="mt-4 flex gap-2">
          <input value={kg} onChange={(e) => setKg(e.target.value)} inputMode="decimal" placeholder="Bugünkü kilon (kg)" className="h-12 min-w-0 flex-1 rounded-xl border border-[#e2d7c6] bg-white px-3 text-sm font-bold outline-none placeholder:font-medium placeholder:text-[#b3a696] focus:border-[#d92835]" />
          <button type="submit" disabled={!kg} className="ember-btn h-12 shrink-0 rounded-xl px-5 text-sm font-extrabold disabled:opacity-50">Kaydet</button>
        </form>
      </section>
      {/* WEIGHT CHART */}
      <section className="rise-in stagger-2 card-paper mt-3 rounded-3xl p-5">
        <SectionHead kicker="Kilo değişimi" title={`Son ${range} gün`} />
        <div className="h-44">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={weights} margin={{ top: 6, right: 4, bottom: 0, left: -14 }}>
              <defs>
                <linearGradient id="wGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#d92835" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#d92835" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#eadfd3" strokeDasharray="3 4" vertical={false} />
              <XAxis dataKey="short" tickLine={false} axisLine={false} tick={{ fill: '#9a8c80', fontSize: 10 }} minTickGap={28} />
              <YAxis domain={['dataMin - 1', 'dataMax + 1']} tickLine={false} axisLine={false} tick={{ fill: '#9a8c80', fontSize: 10 }} width={44} />
              <Tooltip content={<ChartTip suffix="kg" />} />
              <Area type="monotone" dataKey="weight" stroke="#d92835" strokeWidth={2.6} fill="url(#wGrad)" name="Kilo" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>
      {/* CALORIE CHART */}
      <section className="rise-in stagger-3 card-paper mt-3 rounded-3xl p-5">
        <SectionHead kicker="Günlük kalori" right={<span className="rounded-full bg-[#f1ece2] px-2.5 py-1 text-[11px] font-extrabold text-[#6f6259]">Hedef {store.profile.targets.calories}</span>} />
        {calData.every((d) => d.kcal === 0) ? <Empty text="Bu aralıkta öğün kaydı yok — Beslenme sekmesinden ekle, grafik canlansın." /> : (
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={calData} margin={{ top: 6, right: 4, bottom: 0, left: -18 }}>
                <CartesianGrid stroke="#eadfd3" strokeDasharray="3 4" vertical={false} />
                <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: '#9a8c80', fontSize: 10 }} minTickGap={24} />
                <YAxis tickLine={false} axisLine={false} tick={{ fill: '#9a8c80', fontSize: 10 }} width={44} />
                <Tooltip content={<ChartTip suffix="kcal" />} cursor={{ fill: '#f1ece2' }} />
                <Bar dataKey="kcal" radius={[6, 6, 2, 2]} name="Kalori">
                  {calData.map((d, i) => (
                    <Cell key={i} fill={d.kcal >= store.profile.targets.calories * 0.85 ? '#d92835' : '#e4b7a8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
      {/* STEPS CHART */}
      <section className="rise-in stagger-3 card-paper mt-3 rounded-3xl p-5">
        <SectionHead kicker="Adım trendi · otomatik sensör" title={`${avgSteps.toLocaleString('tr-TR')} adım/ort`} />
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={stepData} margin={{ top: 6, right: 4, bottom: 0, left: -14 }}>
              <defs>
                <linearGradient id="sGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#c99a3f" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="#c99a3f" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#eadfd3" strokeDasharray="3 4" vertical={false} />
              <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: '#9a8c80', fontSize: 10 }} minTickGap={28} />
              <YAxis tickLine={false} axisLine={false} tick={{ fill: '#9a8c80', fontSize: 10 }} width={44} tickFormatter={(v: number) => v >= 1000 ? `${Math.round(v / 100) / 10}b` : `${v}`} />
              <Tooltip content={<ChartTip suffix="adım" />} />
              <Area type="monotone" dataKey="adım" stroke="#c99a3f" strokeWidth={2.6} fill="url(#sGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-3">
          <div className="mb-1 flex justify-between text-[11px] font-extrabold"><span className="text-[#6f6259]">10.000 hedefine uzaklık</span><span className="text-[#b97a1a]">%{Math.min(100, Math.round((avgSteps / 10000) * 100))}</span></div>
          <HBar pct={(avgSteps / 10000) * 100} tone="amber" />
        </div>
      </section>
      {/* SLEEP + WATER */}
      <div className="rise-in stagger-4 mt-3 grid grid-cols-1 gap-3">
        <section className="card-paper rounded-3xl p-5">
          <SectionHead kicker="Uyku ritmi" title={sleepData.length ? `${avgSleep} saat/ort` : 'Veri bekleniyor'} />
          {sleepData.length === 0 ? <Empty text="Uyku girilince grafik burada canlanacak — Günlük sekmesinden kaydet." /> : (
            <div className="h-36">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sleepData} margin={{ top: 6, right: 4, bottom: 0, left: -22 }}>
                  <CartesianGrid stroke="#eadfd3" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: '#9a8c80', fontSize: 10 }} minTickGap={24} />
                  <YAxis domain={[0, 12]} tickLine={false} axisLine={false} tick={{ fill: '#9a8c80', fontSize: 10 }} width={40} />
                  <Tooltip content={<ChartTip suffix="saat" />} cursor={{ fill: '#ede9fe' }} />
                  <Bar dataKey="saat" radius={[6, 6, 2, 2]}>
                    {sleepData.map((d, i) => (
                      <Cell key={i} fill={d.saat >= 7 && d.saat <= 9 ? '#7c3aed' : '#c4b5fd'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>
        <section className="card-paper rounded-3xl p-5">
          <SectionHead kicker="Su tüketimi" title="ml / gün" />
          <div className="h-36">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={waterData} margin={{ top: 6, right: 4, bottom: 0, left: -14 }}>
                <CartesianGrid stroke="#eadfd3" strokeDasharray="3 4" vertical={false} />
                <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: '#9a8c80', fontSize: 10 }} minTickGap={24} />
                <YAxis tickLine={false} axisLine={false} tick={{ fill: '#9a8c80', fontSize: 10 }} width={44} tickFormatter={(v: number) => `${Math.round(v / 100) / 10}L`} />
                <Tooltip content={<ChartTip suffix="ml" />} cursor={{ fill: '#dbeafe' }} />
                <Bar dataKey="ml" radius={[6, 6, 2, 2]}>
                  {waterData.map((d, i) => (
                    <Cell key={i} fill={d.ml >= 2000 ? '#2563eb' : '#bfdbfe'} />
                  ))}
                </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
        </section>
      </div>
      {/* volume */}
      <section className="card-paper rise-in mt-3 rounded-3xl p-5">
        <SectionHead kicker="Kas grubu hacmi" title={`Son ${range} gün`} />
        {(() => {
          const agg = new Map<string, number>();
          store.last14.slice(-range).forEach((d) => d.exercises.forEach((e) => agg.set(e.muscle, (agg.get(e.muscle) ?? 0) + e.sets.length)));
          const arr = [...agg.entries()].sort((a, b) => b[1] - a[1]);
          if (!arr.length) return <Empty text="Bu aralıkta antrenman hacmi yok." />;
          const mx = Math.max(...arr.map(([, v]) => v), 1);
          return (
            <div className="space-y-2.5">
              {arr.slice(0, 7).map(([m, s]) => (
                <div key={m}>
                  <div className="mb-1 flex items-center justify-between"><span className="text-xs font-extrabold text-[#1c1512]">{m}</span><span className="text-[11px] font-bold text-[#9a8c80]">{s} set</span></div>
                  <HBar pct={(s / mx) * 100} tone="red" />
                </div>
              ))}
            </div>
          );
        })()}
      </section>
      <p className="mt-2 pb-1 text-center text-[10px] font-bold text-[#b3a696]">Tüm grafikler canlı veriden beslenir · aralık değiştikçe güncellenir</p>
    </div>
  );
}
