import { Check, ChevronLeft, ChevronRight, Dumbbell, Flame, UtensilsCrossed } from 'lucide-react';
import PageHeader from '../lumiere/PageHeader';
import ProgressRing from '../lumiere/ProgressRing';

/**
 * Günlük takip ekranı — love repo `src/routes/app.daily.tsx` tasarımı.
 * Veriler gerçek backend'den gelir (App.jsx çekiyor):
 * nutrition: /api/nutrition/day · workout: /api/workout/day · heatmap: /api/workout/heatmap/day
 */
export default function DailyScreen({
  selectedDate,
  onDateChange,
  shiftDate,
  loading,
  nutrition,
  workout,
  heatmap,
  profile,
  onOpenSettings,
}) {
  const summary = nutrition?.summary || { calories: 0, protein: 0, carbs: 0, fats: 0 };
  const meals = nutrition?.meals || [];
  const logs = workout?.logs || [];

  const targetCal = profile?.daily_calorie_target || 2200;
  const targetProt = profile?.daily_protein_target || 140;
  const totalSets = workout?.total_sets || 0;

  const rings = [
    { value: Math.round(summary.calories || 0), target: targetCal, label: 'Kalori', unit: 'kcal', tone: 'primary' },
    { value: Math.round(summary.protein || 0), target: targetProt, label: 'Protein', unit: 'g', tone: 'success' },
    { value: totalSets, target: 20, label: 'Antrenman', unit: 'set', tone: 'warning' },
  ];

  // Antrenman kayıtlarını harekete göre grupla
  const groupedLogs = logs.reduce((acc, l) => {
    (acc[l.exercise_name] = acc[l.exercise_name] || []).push(l);
    return acc;
  }, {});

  // Isı haritası: {kas_grubu: set_sayısı}
  const heatEntries = Object.entries(heatmap || {})
    .filter(([, v]) => (typeof v === 'number' ? v > 0 : (v?.sets ?? 0) > 0))
    .sort((a, b) => {
      const va = typeof a[1] === 'number' ? a[1] : a[1]?.sets ?? 0;
      const vb = typeof b[1] === 'number' ? b[1] : b[1]?.sets ?? 0;
      return vb - va;
    });

  const dateLabel = (() => {
    try {
      return new Date(`${selectedDate}T12:00:00`).toLocaleDateString('tr-TR', {
        weekday: 'long', day: 'numeric', month: 'long',
      });
    } catch {
      return selectedDate;
    }
  })();

  return (
    <main>
      <PageHeader eyebrow="Günlük takip" title="İlerlemen" onOpenSettings={onOpenSettings} />

      {/* Tarih gezgini */}
      <section className="surface-card flex items-center justify-between gap-2 p-3">
        <button
          type="button"
          onClick={() => shiftDate?.(-1)}
          aria-label="Önceki gün"
          className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-border bg-surface active:scale-95"
        >
          <ChevronLeft size={18} />
        </button>
        <div className="min-w-0 text-center">
          <p className="truncate text-sm font-bold capitalize">{dateLabel}</p>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => e.target.value && onDateChange?.(e.target.value)}
            className="mt-0.5 bg-transparent text-center text-[11px] text-muted-foreground outline-none"
          />
        </div>
        <button
          type="button"
          onClick={() => shiftDate?.(1)}
          aria-label="Sonraki gün"
          className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-border bg-surface active:scale-95"
        >
          <ChevronRight size={18} />
        </button>
      </section>

      {/* Hedef halkaları */}
      <section className="surface-card mt-4 p-5">
        <div className="grid grid-cols-3 gap-2">
          {rings.map((r) => (
            <ProgressRing
              key={r.label}
              value={r.value}
              target={r.target}
              label={r.label}
              unit={r.unit}
              tone={r.tone}
              size={84}
            />
          ))}
        </div>
      </section>

      {/* Öğünler */}
      <section className="surface-card mt-4 p-5">
        <div className="mb-3 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary/15 text-primary-glow">
            <UtensilsCrossed size={16} />
          </span>
          <p className="eyebrow text-muted-foreground">Öğünler</p>
          <span className="rounded-full bg-secondary px-2.5 py-1 text-[11px] font-bold">
            {meals.length} kayıt
          </span>
        </div>
        {loading && <p className="py-3 text-center text-xs text-muted-foreground">Yükleniyor...</p>}
        {!loading && meals.length === 0 && (
          <p className="py-3 text-center text-xs text-muted-foreground">Bu gün için öğün kaydı yok.</p>
        )}
        <div className="space-y-2">
          {meals.map((m, i) => (
            <div key={m.id ?? i} className="flex items-center gap-3 rounded-xl border border-border bg-surface px-3.5 py-2.5">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary/15 text-primary-glow">
                <Flame size={14} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-bold">{m.meal_name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  P {Math.round(m.protein ?? m.target_protein ?? 0)} · K {Math.round(m.carbs ?? m.target_carbs ?? 0)} · Y {Math.round(m.fats ?? m.target_fat ?? 0)}
                </p>
              </div>
              <span className="shrink-0 text-sm font-extrabold">{Math.round(m.calories || 0)}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Antrenman kayıtları */}
      <section className="surface-card mt-4 p-5">
        <div className="mb-3 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-warning/15 text-warning">
            <Dumbbell size={16} />
          </span>
          <p className="eyebrow text-muted-foreground">Antrenman</p>
          <span className="rounded-full bg-secondary px-2.5 py-1 text-[11px] font-bold">{totalSets} set</span>
        </div>
        {!loading && Object.keys(groupedLogs).length === 0 && (
          <p className="py-3 text-center text-xs text-muted-foreground">Bu gün için antrenman kaydı yok.</p>
        )}
        <div className="space-y-2">
          {Object.entries(groupedLogs).map(([name, sets]) => (
            <div key={name} className="rounded-xl border border-border bg-surface px-3.5 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-bold">{name}</p>
                <span className="shrink-0 text-xs font-semibold text-muted-foreground">{sets.length} set</span>
              </div>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                {sets.map((s) => `${s.weight_lifted ?? 0}kg×${s.reps_done ?? 0}`).join(' · ')}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Kas grubu ısı haritası */}
      {heatEntries.length > 0 && (
        <section className="surface-card mt-4 p-5">
          <p className="eyebrow mb-3 text-muted-foreground">Kas grubu yoğunluğu</p>
          <div className="space-y-2.5">
            {heatEntries.map(([muscle, val]) => {
              const sets = typeof val === 'number' ? val : val?.sets ?? 0;
              const maxSets = heatEntries[0] ? (typeof heatEntries[0][1] === 'number' ? heatEntries[0][1] : heatEntries[0][1]?.sets ?? 1) : 1;
              return (
                <div key={muscle}>
                  <div className="mb-1 flex items-center justify-between">
                    <span className="truncate text-xs font-bold capitalize">{muscle.replace(/_/g, ' ')}</span>
                    <span className="shrink-0 text-[11px] font-semibold text-muted-foreground">{sets} set</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-secondary">
                    <div
                      className="ember h-full rounded-full transition-all duration-500"
                      style={{ width: `${maxSets ? (sets / maxSets) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </main>
  );
}
