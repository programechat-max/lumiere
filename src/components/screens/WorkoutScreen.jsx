import { useMemo, useState } from 'react';
import {
  ArrowLeft, Check, ChevronRight, Dumbbell, Sparkles, Timer, TrendingUp, TriangleAlert,
} from 'lucide-react';
import PageHeader from '../lumiere/PageHeader';

/**
 * Antrenman ekranı — love repo `src/routes/app.workout.tsx` tasarımı.
 * Veriler gerçek backend'den gelir (App.jsx çekiyor):
 * workout: /api/workout ({programs, today_logs}) · deloadStatus: /api/workout/deload
 * Program üretimi: POST /api/workout/program/generate (AI)
 */
export default function WorkoutScreen({
  workout,
  deloadStatus,
  workoutError,
  generatingProgram,
  onGenerateProgram,
  metrics,
}) {
  const programs = workout?.programs || [];
  const todayLogs = workout?.today_logs || [];
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [doneSets, setDoneSets] = useState({}); // {exerciseIdx: [setNo, ...]}

  const selected = selectedIdx != null ? programs[selectedIdx] : null;

  const todaySetsByExercise = useMemo(() => {
    const map = {};
    for (const l of todayLogs) {
      map[l.exercise_name] = (map[l.exercise_name] || 0) + 1;
    }
    return map;
  }, [todayLogs]);

  const programProgress = (p) => {
    const total = p.exercises.reduce((s, e) => s + (e.target_sets || 0), 0);
    if (!total) return { done: 0, total: 0, pct: 0 };
    const done = p.exercises.reduce((s, e) => s + Math.min(todaySetsByExercise[e.name] || 0, e.target_sets || 0), 0);
    return { done, total, pct: Math.round((done / total) * 100) };
  };

  // Boş durum — hiç program yokken AI üretimine yönlendir
  if (!programs.length) {
    return (
      <main>
        <PageHeader eyebrow="Antrenman programı" title="Haftalık plan" showSettings={false} />
        <section className="surface-card mt-8 flex flex-col items-center p-8 text-center">
          <span className="ember grid h-14 w-14 place-items-center rounded-2xl">
            <Dumbbell size={24} />
          </span>
          <h2 className="mt-4 text-lg font-extrabold">Henüz programın yok</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Lumiere, profilindeki hedeflere göre sana özel haftalık bir program oluştursun.
          </p>
          {workoutError && (
            <p className="mt-3 rounded-xl border border-warning/40 bg-warning/10 px-3 py-2 text-xs font-semibold text-warning">
              {workoutError}
            </p>
          )}
          <button
            type="button"
            onClick={onGenerateProgram}
            disabled={generatingProgram}
            className="ember ember-glow mt-5 flex h-12 w-full items-center justify-center gap-2 rounded-xl text-sm font-bold active:scale-[0.99] disabled:opacity-60"
          >
            {generatingProgram ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
                Program oluşturuluyor...
              </>
            ) : (
              <>
                <Sparkles size={16} /> AI ile program oluştur
              </>
            )}
          </button>
        </section>
      </main>
    );
  }

  // Gün detayı
  if (selected) {
    const totalEx = selected.exercises.length;
    const doneCount = selected.exercises.filter((e) => (todaySetsByExercise[e.name] || 0) >= (e.target_sets || 1)).length;
    const pct = totalEx ? Math.round((doneCount / totalEx) * 100) : 0;

    return (
      <main>
        <header className="sticky top-0 z-30 -mx-5 mb-4 grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3 border-b border-border bg-background/85 px-5 pb-3 pad-safe-top backdrop-blur-xl">
          <button
            type="button"
            onClick={() => { setSelectedIdx(null); setDoneSets({}); }}
            aria-label="Geri"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-border bg-surface"
          >
            <ArrowLeft size={18} />
          </button>
          <div className="min-w-0">
            <p className="eyebrow text-primary-glow">Antrenman günü</p>
            <h1 className="truncate text-xl font-extrabold">{selected.day_name}</h1>
          </div>
        </header>

        <section className="surface-card p-5">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
            <div className="min-w-0">
              <p className="text-sm font-bold">{doneCount} / {totalEx} hareket tamamlandı</p>
              <p className="text-xs text-muted-foreground">Bugün {todayLogs.length} set kaydedildi</p>
            </div>
            <span className="font-display shrink-0 text-2xl font-extrabold">{pct}%</span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-secondary">
            <div className="ember h-full rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
          </div>
        </section>

        <div className="mt-4 space-y-3">
          {selected.exercises.map((e, i) => {
            const setsDone = todaySetsByExercise[e.name] || 0;
            const target = e.target_sets || 1;
            const isDone = setsDone >= target;
            return (
              <div key={e.id ?? `${e.name}-${i}`} className={`surface-card p-4 ${isDone ? 'border-success/50' : ''}`}>
                <div className="flex items-center gap-3">
                  <span
                    className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl border ${
                      isDone ? 'border-success bg-success/20 text-success' : 'border-border bg-secondary text-muted-foreground'
                    }`}
                  >
                    {isDone ? <Check size={16} /> : <span className="text-xs font-bold">{i + 1}</span>}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className={`truncate text-sm font-bold ${isDone ? 'text-muted-foreground line-through' : ''}`}>
                      {e.name}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {target} set · {e.target_reps} tekrar
                      {setsDone > 0 ? ` · ${setsDone}/${target} set yapıldı` : ''}
                    </p>
                  </div>
                  <span className="flex shrink-0 items-center gap-1 text-[10px] font-semibold text-muted-foreground">
                    <Timer size={13} /> ~{Math.max((e.target_sets || 1) * 3, 5)} dk
                  </span>
                </div>
                {e.progression?.message && (
                  <p className="mt-2.5 flex items-start gap-1.5 rounded-lg bg-secondary px-3 py-2 text-[11px] font-medium text-muted-foreground">
                    <TrendingUp size={13} className="mt-0.5 shrink-0 text-primary-glow" />
                    {e.progression.message}
                  </p>
                )}
              </div>
            );
          })}
        </div>

        <p className="mt-5 mb-2 text-center text-xs text-muted-foreground">
          Setlerini koçuna yazarak kaydedebilirsin — örn. "Bench Press 3 set 80kg 8 tekrar"
        </p>
      </main>
    );
  }

  // Gün listesi
  return (
    <main>
      <PageHeader eyebrow="Antrenman programı" title="Haftalık plan" showSettings={false} />

      {deloadStatus?.needs_deload && (
        <section className="mb-4 flex items-start gap-2.5 rounded-xl border border-warning/40 bg-warning/10 p-3.5">
          <TriangleAlert size={16} className="mt-0.5 shrink-0 text-warning" />
          <div className="min-w-0">
            <p className="text-xs font-bold text-warning">Deload haftası öneriliyor</p>
            <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
              Son antrenmanlarında ilerleme durdu veya yorgunluk yüksek. Koçuna "deload" yazarak hafifletme haftası planlayabilirsin.
            </p>
          </div>
        </section>
      )}

      {workoutError && (
        <p className="mb-4 rounded-xl border border-warning/40 bg-warning/10 px-3.5 py-2.5 text-xs font-semibold text-warning">
          {workoutError}
        </p>
      )}

      <div className="space-y-3">
        {programs.map((p, idx) => {
          const { done, total, pct } = programProgress(p);
          const rest = p.exercises.length === 0;
          const complete = total > 0 && done >= total;
          return (
            <button
              key={p.id ?? idx}
              type="button"
              disabled={rest}
              onClick={() => { setSelectedIdx(idx); setDoneSets({}); }}
              className="surface-card flex w-full items-center gap-3 p-4 text-left disabled:opacity-55"
            >
              <span
                className={`grid h-12 w-12 shrink-0 place-items-center rounded-2xl ${
                  complete ? 'bg-success/15 text-success' : rest ? 'bg-secondary text-muted-foreground' : 'ember'
                }`}
              >
                {complete ? <Check size={19} /> : <Dumbbell size={19} />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-bold">{p.day_name}</span>
                <span className="block truncate text-xs text-muted-foreground">
                  {rest
                    ? 'Dinlenme günü'
                    : total > 0
                      ? `${p.exercises.length} hareket · ${done}/${total} set (%${pct})`
                      : `${p.exercises.length} hareket`}
                </span>
              </span>
              {!rest && <ChevronRight size={18} className="shrink-0 text-muted-foreground" />}
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={onGenerateProgram}
        disabled={generatingProgram}
        className="ember ember-glow mt-5 mb-2 flex h-12 w-full items-center justify-center gap-2 rounded-xl text-sm font-bold active:scale-[0.99] disabled:opacity-60"
      >
        {generatingProgram ? (
          <>
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
            Yeni program oluşturuluyor...
          </>
        ) : (
          <>
            <Sparkles size={16} /> AI ile yeni program oluştur
          </>
        )}
      </button>
    </main>
  );
}
