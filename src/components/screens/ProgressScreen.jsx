import { Scale, Sparkles, TrendingDown, TrendingUp } from 'lucide-react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import PageHeader from '../lumiere/PageHeader';

/**
 * Gelişim ekranı — love repo tasarım diliyle (surface-card + ember).
 * Veriler gerçek backend'den gelir (App.jsx çekiyor):
 * chartData: /api/progress/charts · metrics: /api/metrics · insights: /api/insights
 * Kilo girişi: POST /api/metrics · Analiz: POST /api/insights/generate
 */
export default function ProgressScreen({
  chartData,
  loadingCharts,
  latestWeight,
  weightDelta,
  metrics,
  workout,
  insights,
  analyzing,
  weightInput,
  savingWeight,
  onWeightInputChange,
  onSubmitWeight,
  onRunAnalysis,
  targetCalories,
  targetProtein,
}) {
  const weightData = (chartData?.weight || []).map((w) => ({ ...w, weight: Number(w.weight) }));

  const nutritionData = (chartData?.nutrition || []).map((n) => ({
    date: n.date,
    calories: Math.round(n.calories ?? n.total_calories ?? 0),
    protein: Math.round(n.protein ?? n.total_protein ?? 0),
  }));

  const volumeData = chartData?.volume || [];
  const maxVolume = volumeData.length ? Math.max(...volumeData.map((v) => v.sets || 0), 1) : 1;

  const tooltipStyle = {
    background: 'var(--surface-2)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    color: 'var(--foreground)',
    fontSize: 12,
  };

  return (
    <main>
      <PageHeader eyebrow="Gelişim takibi" title="Gelişimin" showSettings={false} />

      {/* Kilo kartı + giriş */}
      <section className="surface-card p-5">
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
          <div className="min-w-0">
            <p className="eyebrow text-muted-foreground">Güncel kilo</p>
            <p className="mt-1 text-3xl font-extrabold leading-none">
              {latestWeight ? `${latestWeight} kg` : '—'}
            </p>
            {weightDelta != null && (
              <p className={`mt-1.5 flex items-center gap-1 text-xs font-bold ${weightDelta <= 0 ? 'text-success' : 'text-warning'}`}>
                {weightDelta <= 0 ? <TrendingDown size={13} /> : <TrendingUp size={13} />}
                Başlangıçtan beri {weightDelta > 0 ? '+' : ''}{weightDelta.toFixed(1)} kg
              </p>
            )}
          </div>
          <form
            className="flex shrink-0 items-center gap-1.5"
            onSubmit={(e) => { e.preventDefault(); onSubmitWeight?.(); }}
          >
            <input
              type="number"
              step="0.1"
              inputMode="decimal"
              value={weightInput}
              onChange={(e) => onWeightInputChange?.(e.target.value)}
              placeholder="kg"
              className="h-11 w-20 rounded-xl border border-border bg-surface px-3 text-sm font-bold outline-none placeholder:text-muted-foreground"
            />
            <button
              type="submit"
              disabled={savingWeight || !weightInput}
              className="ember grid h-11 w-11 place-items-center rounded-xl active:scale-95 disabled:opacity-60"
              aria-label="Kiloyu kaydet"
            >
              {savingWeight ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
              ) : (
                <Scale size={16} />
              )}
            </button>
          </form>
        </div>
      </section>

      {/* Kilo grafiği */}
      <section className="surface-card mt-4 p-5">
        <p className="eyebrow mb-3 text-muted-foreground">Kilo değişimi</p>
        {loadingCharts ? (
          <div className="grid h-40 place-items-center text-xs text-muted-foreground">Grafikler yükleniyor...</div>
        ) : weightData.length > 1 ? (
          <div className="-ml-2 h-40">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={weightData} margin={{ top: 6, right: 6, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="weightGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.55} />
                    <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fill: 'var(--muted-foreground)', fontSize: 10 }} minTickGap={24} />
                <YAxis domain={['dataMin - 1', 'dataMax + 1']} width={34} tickLine={false} axisLine={false} tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--muted-foreground)' }} />
                <Area type="monotone" dataKey="weight" stroke="var(--primary)" strokeWidth={2.5} fill="url(#weightGrad)" name="Kilo (kg)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="grid h-32 place-items-center text-xs text-muted-foreground">
            Grafik için en az 2 kilo kaydı gerekli.
          </div>
        )}
      </section>

      {/* Kalori grafiği */}
      <section className="surface-card mt-4 p-5">
        <div className="mb-3 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
          <p className="eyebrow text-muted-foreground">Günlük kalori</p>
          <span className="rounded-full bg-secondary px-2.5 py-1 text-[11px] font-bold">Hedef {targetCalories} kcal</span>
        </div>
        {nutritionData.length > 0 ? (
          <div className="-ml-2 h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={nutritionData} margin={{ top: 6, right: 6, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fill: 'var(--muted-foreground)', fontSize: 10 }} minTickGap={24} />
                <YAxis width={34} tickLine={false} axisLine={false} tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--muted-foreground)' }} cursor={{ fill: 'var(--secondary)' }} />
                <Bar dataKey="calories" fill="var(--primary)" radius={[6, 6, 0, 0]} name="Kalori (kcal)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="grid h-32 place-items-center text-xs text-muted-foreground">Henüz beslenme geçmişi yok.</div>
        )}
      </section>

      {/* Haftalık hacim (kas grubu) */}
      <section className="surface-card mt-4 p-5">
        <p className="eyebrow mb-3 text-muted-foreground">Haftalık hacim — kas grubu</p>
        {volumeData.length === 0 ? (
          <p className="py-3 text-center text-xs text-muted-foreground">Henüz antrenman hacmi yok.</p>
        ) : (
          <div className="space-y-2.5">
            {volumeData.slice(0, 8).map((v) => (
              <div key={v.muscle_group}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="truncate text-xs font-bold capitalize">{(v.muscle_group || '').replace(/_/g, ' ')}</span>
                  <span className="shrink-0 text-[11px] font-semibold text-muted-foreground">{v.sets} set</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-secondary">
                  <div className="ember h-full rounded-full" style={{ width: `${(v.sets / maxVolume) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Koç analizleri */}
      <section className="surface-card mt-4 mb-2 p-5">
        <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary/15 text-primary-glow">
            <Sparkles size={16} />
          </span>
          <p className="eyebrow text-muted-foreground">Koç analizleri</p>
          <button
            type="button"
            onClick={onRunAnalysis}
            disabled={analyzing}
            className="ember flex h-9 items-center gap-1.5 rounded-full px-3.5 text-xs font-bold active:scale-95 disabled:opacity-60"
          >
            {analyzing ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-background border-t-transparent" />
            ) : (
              <Sparkles size={13} />
            )}
            {analyzing ? 'Analiz ediliyor' : 'Analiz et'}
          </button>
        </div>
        {(insights || []).length === 0 ? (
          <p className="py-3 text-center text-xs text-muted-foreground">
            Henüz analiz yok. "Analiz et" ile koçunun bu haftaki değerlendirmesini al.
          </p>
        ) : (
          <div className="mt-3 space-y-2">
            {insights.slice(0, 8).map((ins) => (
              <div key={ins.id} className="rounded-xl border border-border bg-surface px-3.5 py-2.5">
                <p className="text-[10px] font-mono uppercase tracking-wide text-primary-glow">{ins.category}</p>
                <p className="mt-0.5 text-xs leading-relaxed">{ins.content}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
