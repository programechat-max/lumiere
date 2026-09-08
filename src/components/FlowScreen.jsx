import { useMemo } from 'react';
import {
  ChevronRight, Dumbbell, Flame, Camera, Sparkles, TrendingDown,
  LineChart, LogOut, ShieldCheck,
} from 'lucide-react';
import PageHeader from './lumiere/PageHeader';
import ProgressRing from './lumiere/ProgressRing';
import * as authService from '../services/authService';

const TR_DAYS = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'];

/**
 * Ana akış ekranı — love repo `src/routes/app.flow.tsx` tasarımı.
 * Veriler gerçek backend'den gelir (App.jsx çekiyor):
 * profile: /api/profile · workout: /api/workout · nutritionPlans: /api/nutrition
 */
export default function FlowScreen({
  profile,
  workout,
  nutritionPlans,
  onQuickAction,
  onNavigateTab,
  onSetChatMessage,
  onOpenSettings,
  onLogout,
  memberSinceLabel,
  isAdmin,
  onOpenAdmin,
}) {
  const firstName = (authService.getStoredUser()?.full_name || '').trim().split(' ')[0] || 'Sporcu';

  const programs = workout?.programs || [];
  const todayLogs = workout?.today_logs || [];

  // Bugünün program günü: önce gün adına göre eşle, olmazsa sırayla dön.
  const todayProgram = useMemo(() => {
    if (!programs.length) return null;
    const todayName = TR_DAYS[(new Date().getDay() + 6) % 7];
    const byName = programs.find((p) => (p.day_name || '').toLowerCase().includes(todayName.toLowerCase()));
    return byName || programs[(new Date().getDay() + 6) % 7 % programs.length];
  }, [programs]);

  const consumedCal = (nutritionPlans || []).reduce((s, m) => s + (m.calories || 0), 0);
  const consumedProt = (nutritionPlans || []).reduce((s, m) => s + (m.target_protein ?? m.protein ?? 0), 0);
  const targetCal = profile?.daily_calorie_target || 2200;
  const targetProt = profile?.daily_protein_target || 140;
  const todayTargetSets = (todayProgram?.exercises || []).reduce((s, e) => s + (e.target_sets || 0), 0);

  const rings = [
    { value: Math.round(consumedCal), target: targetCal, label: 'Kalori', unit: 'kcal', tone: 'primary' },
    { value: Math.round(consumedProt), target: targetProt, label: 'Protein', unit: 'g', tone: 'success' },
    { value: todayLogs.length, target: todayTargetSets, label: 'Antrenman', unit: 'set', tone: 'warning' },
  ];

  const goChat = () => {
    onSetChatMessage?.('');
    onNavigateTab?.('chat');
  };

  return (
    <main>
      <PageHeader
        eyebrow={`Merhaba ${firstName}`}
        title="Bugünün akışı"
        onOpenSettings={onOpenSettings}
        action={isAdmin && (
          <button
            type="button"
            onClick={onOpenAdmin}
            aria-label="Yönetim paneli"
            className="grid h-10 w-10 place-items-center rounded-full border border-border bg-surface text-primary-glow active:scale-95"
          >
            <ShieldCheck size={18} />
          </button>
        )}
      />

      {/* Bugünün odağı — gerçek program verisi */}
      <section className="surface-card relative overflow-hidden p-5">
        <div className="hero-bg absolute inset-0 opacity-90" aria-hidden />
        <div className="relative">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
            <div className="min-w-0">
              <p className="eyebrow text-primary-glow">Bugünün odağı</p>
              <h2 className="mt-1 text-2xl font-extrabold leading-tight">
                {todayProgram ? todayProgram.day_name : 'Dinlenme'}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {todayProgram
                  ? `${todayProgram.exercises.length} hareket · ~${Math.max(todayProgram.exercises.length * 10, 20)} dk`
                  : 'Program oluşturulmadı'}
              </p>
            </div>
            <span className="ember grid h-12 w-12 shrink-0 place-items-center rounded-2xl">
              <Dumbbell size={22} />
            </span>
          </div>

          <div className="mt-5 h-2 overflow-hidden rounded-full bg-secondary">
            <div
              className="ember h-full rounded-full transition-all duration-500"
              style={{ width: `${todayTargetSets ? Math.min((todayLogs.length / todayTargetSets) * 100, 100) : 0}%` }}
            />
          </div>

          <button
            type="button"
            onClick={() => onNavigateTab?.('workout')}
            className="ember ember-glow mt-4 flex h-12 w-full items-center justify-center gap-1.5 rounded-xl text-sm font-bold active:scale-[0.99]"
          >
            {todayProgram ? 'Antrenmanı başlat' : 'Program oluştur'} <ChevronRight size={17} />
          </button>
        </div>
      </section>

      {/* Günlük durum halkaları — gerçek /api/nutrition + /api/workout verisi */}
      <section className="surface-card mt-4 p-5">
        <p className="eyebrow mb-4 text-muted-foreground">Günlük durum</p>
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

      {/* AI koç köprüsü */}
      <section className="surface-card mt-4 p-5">
        <div className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3">
          <span className="ember grid h-11 w-11 shrink-0 place-items-center rounded-2xl">
            <Sparkles size={19} />
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold">Lumiere yanında</p>
            <p className="truncate text-xs text-muted-foreground">Bugün nasıl hissediyorsun?</p>
          </div>
        </div>
        <button
          type="button"
          onClick={goChat}
          className="mt-4 flex h-12 w-full items-center justify-between rounded-xl border border-border bg-surface px-4 text-sm text-muted-foreground"
        >
          Koçuna bir şey sor... <ChevronRight size={17} />
        </button>
      </section>

      {/* Hızlı aksiyonlar */}
      <section className="mt-4 grid grid-cols-2 gap-3">
        <button type="button" onClick={() => onNavigateTab?.('nutrition')} className="surface-card p-4 text-left">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/15 text-primary-glow">
            <Flame size={18} />
          </span>
          <p className="mt-3 text-sm font-bold">Öğün ekle</p>
          <p className="text-xs text-muted-foreground">{Math.round(consumedCal)} / {targetCal} kcal</p>
        </button>
        <button type="button" onClick={() => onNavigateTab?.('nutrition')} className="surface-card p-4 text-left">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-success/15 text-success">
            <Camera size={18} />
          </span>
          <p className="mt-3 text-sm font-bold">Foto analizi</p>
          <p className="text-xs text-muted-foreground">Makroları otomatik bul</p>
        </button>
      </section>

      {/* Kilo değişimi + gelişim köprüsü */}
      <section className="surface-card mt-4 p-5">
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
          <div className="min-w-0">
            <p className="eyebrow text-muted-foreground">Kilo değişimi</p>
            <p className="mt-1 text-2xl font-extrabold">
              {profile?.current_weight ? `${profile.current_weight} kg` : '—'}
            </p>
          </div>
          <span className="flex shrink-0 items-center gap-1 rounded-full bg-success/15 px-3 py-1.5 text-xs font-bold text-success">
            <TrendingDown size={14} /> {profile?.target_weight ? `Hedef ${profile.target_weight} kg` : 'Hedef —'}
          </span>
        </div>
        <button
          type="button"
          onClick={() => onNavigateTab?.('progress')}
          className="mt-4 flex h-12 w-full items-center justify-between rounded-xl border border-border bg-surface px-4 text-sm font-semibold"
        >
          <span className="flex items-center gap-2"><LineChart size={16} className="text-primary-glow" /> Grafiklerini gör</span>
          <ChevronRight size={17} className="text-muted-foreground" />
        </button>
      </section>

      {/* Üyelik / oturum */}
      <section className="surface-card mt-4 mb-2 p-5">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="eyebrow text-muted-foreground">Üyelik</p>
            <p className="mt-1 truncate text-sm font-bold">{memberSinceLabel || 'Lumiere üyesi'}</p>
          </div>
          <button
            type="button"
            onClick={onLogout}
            className="flex shrink-0 items-center gap-1.5 rounded-full border border-border px-3.5 py-2 text-xs font-bold text-muted-foreground active:scale-95"
          >
            <LogOut size={13} /> Çıkış
          </button>
        </div>
      </section>
    </main>
  );
}
