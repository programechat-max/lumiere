import { useEffect, useRef, useState } from 'react';
import { Check, ChevronRight, Dumbbell, Plus, RotateCcw, Timer } from 'lucide-react';
import { DayNavigator, Empty, HBar, SectionHead } from './chrome';
import type { Store } from '../lib/store';
import { isToday, todayISO } from '../lib/utils';

export function WorkoutScreen({ store }: { store: Store }) {
  const iso = store.selectedDate;
  const prog = store.programFor(iso);
  const logs = store.workoutFor(iso);
  const done = store.doneMap[iso] ?? {};
  const editable = isToday(iso);
  const [kg, setKg] = useState('40');
  const [reps, setReps] = useState('10');
  const [exName, setExName] = useState('Bench Press');
  const [rest, setRest] = useState(0);
  const restRef = useRef<number | null>(null);

  useEffect(() => () => { if (restRef.current) window.clearInterval(restRef.current); }, []);
  const startRest = (sec: number) => {
    if (restRef.current) window.clearInterval(restRef.current);
    setRest(sec);
    restRef.current = window.setInterval(() => {
      setRest((r) => {
        if (r <= 1) { if (restRef.current) window.clearInterval(restRef.current); return 0; }
        return r - 1;
      });
    }, 1000);
  };

  const totalSets = prog ? prog.exercises.reduce((s, e) => s + e.sets, 0) : 0;
  const doneCount = prog ? prog.exercises.filter((e) => done[e.name]).length : 0;
  const loggedSets = logs.reduce((s, e) => s + e.sets.length, 0);

  return (
    <div>
      <div className="rise-in">
        <p className="eyebrow text-[#d92835]">Antrenman</p>
        <h1 className="font-display mt-1.5 text-[30px] font-extrabold leading-tight">Güç günü<span className="text-[#d92835]">.</span></h1>
      </div>
      <div className="rise-in stagger-1 mt-4">
        <DayNavigator iso={iso} onChange={store.setSelectedDate} onShift={store.shiftSelectedDate} note={isToday(iso) ? 'Bugünkü programın ve kayıtların' : 'Yalnızca seçili günün programı ve kayıtları'} />
      </div>
      {/* program */}
      <section className="rise-in stagger-2 card-paper mt-3 overflow-hidden rounded-3xl">
        <div className="bg-[#1c1512] p-5 text-white">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="eyebrow text-[#ff8a7a]">{prog ? prog.dayName : 'Dinlenme'} · {prog?.duration ?? ''}</p>
              <h3 className="font-display mt-1 text-xl font-extrabold">{prog ? prog.focus : 'Aktif dinlenme'}</h3>
            </div>
            <span className="ember-btn grid h-12 w-12 shrink-0 place-items-center rounded-2xl"><Dumbbell size={22} /></span>
          </div>
          {prog && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-[11px] font-extrabold text-white/70"><span>{doneCount}/{prog.exercises.length} hareket</span><span>{totalSets} set planlı</span></div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/12">
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${(doneCount / Math.max(1, prog.exercises.length)) * 100}%`, background: 'linear-gradient(90deg,#ff5a63,#ffb199)' }} />
              </div>
            </div>
          )}
        </div>
        <div className="space-y-2 p-4">
          {!prog && <Empty text="Bu gün dinlenme — yürüyüş + esneme önerilir." />}
          {prog?.exercises.map((e) => {
            const isDone = !!done[e.name];
            return (
              <div key={e.name} className={`flex items-center gap-3 rounded-2xl border p-3.5 transition ${isDone ? 'border-[#2e9e5b]/40 bg-[#e8f6ee]/60' : 'border-[#ece2d2] bg-white'}`}>
                <button
                  disabled={!editable}
                  onClick={() => store.toggleDone(iso, e.name)}
                  aria-label={`${e.name} tamamlandı`}
                  className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl transition active:scale-90 ${isDone ? 'bg-[#2e9e5b] text-white' : 'border-2 border-[#ddd0bd] text-transparent'}`}
                >
                  <Check size={17} strokeWidth={3} />
                </button>
                <div className="min-w-0 flex-1">
                  <p className={`truncate text-sm font-extrabold ${isDone ? 'text-[#2e9e5b] line-through' : 'text-[#1c1512]'}`}>{e.name}</p>
                  <p className="text-[11px] font-semibold text-[#9a8c80]">{e.muscle} · {e.sets}×{e.reps} · dinlenme {e.rest}</p>
                </div>
                <button onClick={() => startRest(90)} className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#f1ece2] text-[#6f6259] transition active:scale-90" aria-label="Dinlenme sayacı"><Timer size={16} /></button>
              </div>
            );
          })}
          {!editable && prog && <p className="px-1 text-center text-[11px] font-bold text-[#9a8c80]">Geçmiş gün — tamamlama işaretleri salt okunur</p>}
        </div>
      </section>
      {/* rest timer */}
      {(rest > 0) && (
        <section className="card-paper mt-3 flex items-center gap-3 rounded-3xl border-[#d92835]/30 bg-gradient-to-r from-[#fde1df] to-white p-4">
          <span className="ember-btn grid h-11 w-11 shrink-0 place-items-center rounded-2xl"><Timer size={20} /></span>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-extrabold uppercase tracking-widest text-[#8f1826]">Dinlenme</p>
            <p className="font-display text-2xl font-extrabold text-[#1c1512]">{Math.floor(rest / 60)}:{String(rest % 60).padStart(2, '0')}</p>
          </div>
          <button onClick={() => { if (restRef.current) window.clearInterval(restRef.current); setRest(0); }} className="flex items-center gap-1 rounded-full bg-[#1c1512] px-3.5 py-2 text-xs font-extrabold text-white"><RotateCcw size={13} /> Bitir</button>
        </section>
      )}
      {/* quick rest presets */}
      <div className="mt-3 flex gap-2">
        {[60, 90, 120].map((s) => (
          <button key={s} onClick={() => startRest(s)} className="flex-1 rounded-2xl border border-[#e7ddcf] bg-white py-2.5 text-xs font-extrabold text-[#6f6259] transition active:scale-95">
            {s >= 60 ? `${s / 60} dk` : `${s} sn`} sayaç
          </button>
        ))}
      </div>
      {/* log set (today only) */}
      <section className="card-paper rise-in mt-3 rounded-3xl p-5">
        <SectionHead kicker="Set kaydı" title={editable ? 'Bugüne set ekle' : 'Kayıtlı setler'} right={<span className="rounded-full bg-[#f1ece2] px-2.5 py-1 text-[11px] font-extrabold text-[#6f6259]">{loggedSets} set</span>} />
        {editable ? (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              const k = parseFloat(kg.replace(',', '.')) || 0;
              const r = parseInt(reps, 10) || 0;
              if (!exName.trim() || r <= 0) return;
              store.addExercise(todayISO(), { name: exName.trim(), muscle: 'Genel', sets: [{ kg: k, reps: r }] });
              startRest(90);
            }}
          >
            <input value={exName} onChange={(e) => setExName(e.target.value)} placeholder="Hareket" className="h-12 min-w-0 flex-[1.4] rounded-xl border border-[#e2d7c6] bg-white px-3 text-sm font-bold outline-none focus:border-[#d92835]" />
            <input value={kg} onChange={(e) => setKg(e.target.value)} inputMode="decimal" placeholder="kg" className="h-12 w-16 rounded-xl border border-[#e2d7c6] bg-white px-2 text-center text-sm font-bold outline-none focus:border-[#d92835]" />
            <input value={reps} onChange={(e) => setReps(e.target.value)} inputMode="numeric" placeholder="tk" className="h-12 w-14 rounded-xl border border-[#e2d7c6] bg-white px-2 text-center text-sm font-bold outline-none focus:border-[#d92835]" />
            <button type="submit" className="ember-btn grid h-12 w-12 shrink-0 place-items-center rounded-xl" aria-label="Set ekle"><Plus size={19} strokeWidth={2.6} /></button>
          </form>
        ) : null}
        <div className="mt-3 space-y-2">
          {logs.length === 0 && <Empty text={editable ? 'Henüz set yok — ilk setini logla.' : 'Bu güne ait set kaydı yok.'} />}
          {logs.map((l, i) => (
            <div key={`${l.name}-${i}`} className="flex items-center justify-between gap-2 rounded-2xl border border-[#ece2d2] bg-white px-3.5 py-2.5">
              <p className="truncate text-sm font-extrabold text-[#1c1512]">{l.name}</p>
              <p className="shrink-0 text-[11px] font-bold text-[#9a8c80]">{l.sets.map((s) => `${s.kg}kg×${s.reps}`).join(' · ')}</p>
            </div>
          ))}
        </div>
      </section>
      {/* heat */}
      {logs.length > 0 && (
        <section className="card-paper mt-3 rounded-3xl p-5">
          <SectionHead kicker="Bu günün hacmi" />
          <HBar pct={(loggedSets / Math.max(1, totalSets || 20)) * 100} tone="red" />
          <p className="mt-2 text-xs font-bold text-[#6f6259]">{loggedSets} set kaydedildi{totalSets ? ` · plan ${totalSets} set` : ''}</p>
        </section>
      )}
      <button
        onClick={() => { void store.regenerateProgram(); }}
        disabled={store.regenerating}
        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-2xl border border-[#e7ddcf] bg-white py-3 text-sm font-extrabold text-[#6f6259] disabled:opacity-60"
      >
        {store.regenerating ? 'AI programı oluşturuyor…' : <>Programı AI ile yenile <ChevronRight size={16} /></>}
      </button>
    </div>
  );
}
