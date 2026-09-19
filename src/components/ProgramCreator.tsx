// Lumiere Program Oluşturucu — profil verisinden kişiselleştirilmiş beslenme
// hedefleri + haftalık antrenman programı + öğün planı üretir ve önizler.
// Üretim anında (istemci tarafı planner ile) tamamlanır; AI koç arka planda
// daha detaylı programı hazırlayıp devreye alır.
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Calculator, Check, Dumbbell, Flame, Sparkles, UtensilsCrossed } from 'lucide-react';
import { Logo } from './chrome';
import { buildMealPlan, buildWeeklySplit, computeNutrition, splitLabel, type PlannerInput } from '../lib/planner';
import type { Store } from '../lib/store';

const STAGES = [
  { Icon: Calculator, t: 'Metabolizman hesaplanıyor', d: 'BMR ve günlük enerji ihtiyacı' },
  { Icon: Flame, t: 'Kalori & makro hedeflerin belirleniyor', d: 'Hedefine göre açık/fazlalık kurgusu' },
  { Icon: Dumbbell, t: 'Haftalık antrenman splitin kurgulanıyor', d: 'Seviyene ve gün sayına göre' },
  { Icon: UtensilsCrossed, t: 'Beslenme planın hazırlanıyor', d: 'Tercihine göre öğün şablonları' },
];

export function ProgramCreator({ store, done }: { store: Store; done: () => void }) {
  const input: PlannerInput = useMemo(() => ({
    gender: store.profile.gender || 'Erkek',
    age: store.profile.age || 27,
    heightCm: store.profile.heightCm || 175,
    weightKg: store.profile.currentWeight,
    targetWeightKg: store.profile.targetWeight,
    goal: store.profile.goal,
    level: store.profile.level,
    days: store.profile.workoutDays || 3,
    diet: store.profile.diet || 'Dengeli',
  }), [store.profile]);

  const nutrition = useMemo(() => computeNutrition(input), [input]);
  const programs = useMemo(() => buildWeeklySplit(input), [input]);
  const meals = useMemo(() => buildMealPlan(input, nutrition.targets), [input, nutrition]);

  const [stage, setStage] = useState(-1);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState('');
  useEffect(() => {
    const timers = STAGES.map((_, i) => window.setTimeout(() => setStage(i), 450 + i * 700));
    const finish = window.setTimeout(() => setStage(STAGES.length), 450 + STAGES.length * 700 + 350);
    return () => { timers.forEach((t) => window.clearTimeout(t)); window.clearTimeout(finish); };
  }, []);
  const generating = stage < STAGES.length;

  const trainingDays = programs.filter((p) => p.exercises.length > 0);
  const apply = async () => {
    setApplying(true);
    setApplyError('');
    try {
      await store.completeOnboarding({
      goal: input.goal,
      level: input.level,
      weight: input.weightKg,
      targetWeight: input.targetWeightKg,
      targets: nutrition.targets,
      gender: input.gender,
      age: input.age,
      heightCm: input.heightCm,
      diet: input.diet,
      days: input.days,
      videoAnalysis: store.onboardingVideo ?? null,
      bodyComposition: store.onboardingBodyComposition ?? null,
      });
      await store.generateKnowledgePlans(input.days, input.diet);
      done();
    } catch (error) {
      setApplyError(error instanceof Error ? error.message : 'Plan oluşturulamadı.');
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="min-h-dvh bg-[#f4f1ec] text-[#1c1512]">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-32 left-1/2 h-80 w-[560px] -translate-x-1/2 rounded-full bg-[#d92835]/12 blur-[100px]" />
        <div className="absolute -bottom-40 -left-24 h-80 w-80 rounded-full bg-[#c99a3f]/15 blur-[90px]" />
      </div>
      <div className="relative mx-auto flex min-h-dvh w-full max-w-md flex-col px-6 pb-10 pt-[max(2rem,env(safe-area-inset-top))]">
        <Logo />
        {generating ? (
          <div className="flex flex-1 flex-col justify-center">
            <p className="eyebrow text-[#d92835]">Program oluşturucu</p>
            <h1 className="font-display mt-2 text-[32px] font-extrabold leading-[1.05]">Planın<br />hazırlanıyor<span className="text-[#d92835]">.</span></h1>
            <div className="mt-8 space-y-2.5">
              {STAGES.map((s, i) => {
                const doneStage = stage > i;
                const active = stage === i;
                return (
                  <div key={s.t} className={`flex items-center gap-3.5 rounded-2xl border-2 p-4 transition-all duration-500 ${doneStage ? 'border-[#4cc38a]/40 bg-white' : active ? 'border-[#d92835] bg-white shadow-[0_14px_30px_-18px_rgba(217,40,53,0.5)]' : 'border-[#e7ddcf] bg-white/40 opacity-50'}`}>
                    <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl ${doneStage ? 'bg-[#e8f6ee] text-[#2e9e5b]' : active ? 'ember-btn' : 'bg-[#f4f1ec] text-[#9a8c80]'}`}>
                      {doneStage ? <Check size={20} strokeWidth={3} /> : <s.Icon size={20} />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[14px] font-extrabold">{s.t}</span>
                      <span className="block text-xs font-medium text-[#9a8c80]">{s.d}</span>
                    </span>
                    {active && <span className="h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-[#e2d7c6] border-t-[#d92835]" />}
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div key="preview" className="rise-in flex-1 py-6">
            <p className="eyebrow text-[#d92835]">Kişisel planın hazır</p>
            <h1 className="font-display mt-2 text-[30px] font-extrabold leading-[1.05]">Sana özel<br />kurgulandı<span className="text-[#d92835]">.</span></h1>
            {/* KPI */}
            <div className="mt-5 grid grid-cols-2 gap-2">
              <div className="card-paper rounded-2xl p-4">
                <p className="eyebrow text-[#d92835]">Günlük kalori</p>
                <p className="font-display mt-1 text-[26px] font-extrabold leading-none">{nutrition.targets.calories.toLocaleString('tr-TR')}<span className="text-xs font-bold text-[#9a8c80]"> kcal</span></p>
              </div>
              <div className="card-paper rounded-2xl p-4">
                <p className="eyebrow text-[#b97a1a]">Protein</p>
                <p className="font-display mt-1 text-[26px] font-extrabold leading-none">{nutrition.targets.protein}<span className="text-xs font-bold text-[#9a8c80]"> g</span></p>
              </div>
              <div className="card-paper rounded-2xl p-4">
                <p className="eyebrow text-[#b3a696]">BMR</p>
                <p className="font-display mt-1 text-[20px] font-extrabold leading-none">{nutrition.bmr.toLocaleString('tr-TR')}<span className="text-xs font-bold text-[#9a8c80]"> kcal</span></p>
              </div>
              <div className="card-paper rounded-2xl p-4">
                <p className="eyebrow text-[#b3a696]">TDEE</p>
                <p className="font-display mt-1 text-[20px] font-extrabold leading-none">{nutrition.tdee.toLocaleString('tr-TR')}<span className="text-xs font-bold text-[#9a8c80]"> kcal</span></p>
              </div>
            </div>
            <p className="mt-2 rounded-xl bg-[#f8f4ec] px-3.5 py-2.5 text-center text-[11px] font-bold text-[#6f6259]">{nutrition.strategy} · {input.diet} beslenme · {splitLabel(input.days)}</p>
            {/* Haftalık split */}
            <div className="card-paper mt-3 rounded-3xl p-5">
              <p className="eyebrow text-[#b3a696]">Haftalık antrenman programın</p>
              <div className="mt-3 space-y-1.5">
                {programs.map((p) => {
                  const rest = p.exercises.length === 0;
                  const sets = p.exercises.reduce((s, e) => s + e.target_sets, 0);
                  const focus = rest ? 'Aktif dinlenme' : [...new Set(p.exercises.map((e) => e.muscle_group ?? 'Genel'))].join(' · ');
                  return (
                    <div key={p.id} className={`flex items-center gap-3 rounded-xl px-3.5 py-2.5 ${rest ? 'bg-[#f8f4ec]/60' : 'bg-[#f8f4ec]'}`}>
                      <span className={`w-20 shrink-0 text-[11px] font-extrabold ${rest ? 'text-[#b3a696]' : 'text-[#d92835]'}`}>{p.day_name.slice(0, 3).toUpperCase()}</span>
                      <span className="min-w-0 flex-1">
                        <span className={`block truncate text-[13px] font-extrabold ${rest ? 'text-[#9a8c80]' : 'text-[#1c1512]'}`}>{focus}</span>
                      </span>
                      <span className="shrink-0 text-[11px] font-bold text-[#9a8c80]">{rest ? 'dinlen' : `${p.exercises.length} hareket · ${sets} set`}</span>
                    </div>
                  );
                })}
              </div>
            </div>
            {/* Beslenme planı */}
            <div className="card-paper mt-3 rounded-3xl p-5">
              <p className="eyebrow text-[#b3a696]">Beslenme planın · {input.diet}</p>
              <div className="mt-3 space-y-1.5">
                {meals.map((m) => (
                  <div key={m.time} className="flex items-center gap-3 rounded-xl bg-[#f8f4ec] px-3.5 py-2.5">
                    <span className="w-11 shrink-0 text-[11px] font-extrabold text-[#9a8c80]">{m.time}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13px] font-extrabold text-[#1c1512]">{m.name}</span>
                      <span className="block truncate text-[11px] font-medium text-[#9a8c80]">{m.detail}</span>
                    </span>
                    <span className="shrink-0 text-[11px] font-extrabold text-[#d92835]">{m.calories} kcal</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2 rounded-2xl bg-[#1c1512] p-4 text-white">
              <Sparkles size={18} className="shrink-0 text-[#ff5a63]" />
              <p className="text-xs font-semibold leading-relaxed">Bu ekran yalnızca önizlemedir. Onayladığında gerçek planın video analizi, kanıt kütüphanesi ve güvenli hacim sınırlarıyla oluşturulur.</p>
            </div>
            {applyError && <p className="mt-3 rounded-xl bg-[#fde1df] px-3 py-2.5 text-xs font-bold text-[#8f1826]">{applyError}</p>}
            <button onClick={() => void apply()} disabled={applying} className="ember-btn mt-4 flex w-full items-center justify-center gap-2 rounded-2xl py-4 text-[15px] font-extrabold disabled:opacity-60">
              {applying ? 'Bilimsel planın oluşturuluyor…' : <>Planımı uygula ve başla <ArrowRight size={18} /></>}
            </button>
            <p className="mt-2 pb-1 text-center text-[10px] font-bold text-[#b3a696]">{trainingDays.length} antrenman günü · {programs.reduce((s, p) => s + p.exercises.length, 0)} hareket · {nutrition.targets.calories.toLocaleString('tr-TR')} kcal/gün</p>
          </div>
        )}
      </div>
    </div>
  );
}
