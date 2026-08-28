import { useState, useRef, useEffect, useCallback } from 'react';
import { Camera, Sparkles, Zap, BarChart2, Target, ChevronRight, Dumbbell, UtensilsCrossed } from 'lucide-react';
import QuickJarvisInput from './QuickJarvisInput';
import QuickActionCard from './QuickActionCard';

/**
 * FlowScreen - Lumiere Coaching mobil uygulamasının ana "Akış" (Home/Feed) ekranı
 *
 * Tasarım Felsefesi:
 * - Above-the-fold: Tüm kritik aksiyonlar ilk bakışta görünür, scroll gerekmez
 * - Ergonomik: Başparmak erişim alanına uygun, kompakt layout
 * - Glassmorphism: Cam efekti, yumuşak gölgeler, premium his
 * - Micro-interactions: Hover/tap animasyonları, loading states
 * - Modüler: Her bileşen kendi sorumluluğunda, yeniden kullanılabilir
 */
export default function FlowScreen({
  profile,
  workout,
  nutritionPlans,
  metrics,
  insights,
  onQuickAction,
  onNavigateTab,
  onSetChatMessage
}) {
  const scrollRef = useRef(null);
  const [isScrolled, setIsScrolled] = useState(false);
  const [jarvisInput, setJarvisInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  // Scroll listener for dynamic header/background effects
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = scrollRef.current?.scrollTop || 0;
      setIsScrolled(scrollY > 20);
    };

    const element = scrollRef.current;
    element?.addEventListener('scroll', handleScroll, { passive: true });
    return () => element?.removeEventListener('scroll', handleScroll);
  }, []);

  // Quick Jarvis message handler
  const handleJarvisSubmit = useCallback(async (message) => {
    if (!message.trim() || isProcessing) return;

    setIsProcessing(true);
    try {
      // Set chat message and navigate to chat tab
      if (onSetChatMessage) {
        onSetChatMessage(message);
      }
      if (onNavigateTab) {
        onNavigateTab('chat');
      }

      // If we have a callback for cross-tab communication, use it
      if (onQuickAction) {
        onQuickAction('chat', { message });
      }
    } catch (error) {
      console.error('Jarvis navigation error:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [onNavigateTab, onSetChatMessage, onQuickAction, isProcessing]);

  // Quick action handlers
  const handleNutritionPhoto = useCallback(() => {
    if (onQuickAction) onQuickAction('nutrition-photo');
    if (onNavigateTab) {
      onNavigateTab('nutrition');
      // Could also trigger photo action via callback
    }
  }, [onNavigateTab, onQuickAction]);

  const handleFormPhoto = useCallback(() => {
    if (onQuickAction) onQuickAction('form-photo');
    if (onNavigateTab) {
      onNavigateTab('progress');
    }
  }, [onNavigateTab, onQuickAction]);

  // Calculate quick stats for the header
  const consumedCalories = nutritionPlans?.reduce((acc, plan) => acc + (plan.calories || 0), 0) || 0;
  const consumedProtein = nutritionPlans?.reduce((acc, plan) => acc + (plan.target_protein || 0), 0) || 0;
  const targetCalories = profile?.daily_calorie_target || 2200;
  const targetProtein = profile?.daily_protein_target || 140;
  const caloriePercent = targetCalories > 0 ? Math.min((consumedCalories / targetCalories) * 100, 100) : 0;
  const proteinPercent = targetProtein > 0 ? Math.min((consumedProtein / targetProtein) * 100, 100) : 0;

  const hasActiveProgram = workout?.programs?.length > 0;
  const todayWorkoutCount = workout?.today_logs?.length || 0;

  return (
    <div className="flow-screen min-h-screen bg-neutral-950">
      {/* Dynamic Background Atmosphere */}
      <div className={`flow-atmosphere fixed inset-0 pointer-events-none z-0 transition-opacity duration-500 ${isScrolled ? 'opacity-50' : 'opacity-100'}`}>
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[300%] h-[300%] bg-gradient-to-br from-orange-500/10 via-transparent to-emerald-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-0 w-[200%] h-[200%] bg-gradient-to-tl from-orange-500/5 via-transparent to-emerald-500/5 rounded-full blur-3xl" />
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 main-grid-bg opacity-30" />
      </div>

      {/* Main Scrollable Content */}
      <div
        ref={scrollRef}
        className="flow-content relative z-10 min-h-screen overflow-y-auto"
        style={{
          paddingBottom: 'calc(env(safe-area-inset-bottom) + 100px)' // Space for bottom nav
        }}
      >
        {/* ==========================================
             SECTION 1: QUICK JARVIS INPUT (Above the Fold)
             ========================================== */}
        <QuickJarvisInput
          value={jarvisInput}
          onChange={setJarvisInput}
          onSubmit={handleJarvisSubmit}
          disabled={isProcessing}
          placeholder="Jarvis'e sor..."
        />

        {/* ==========================================
             SECTION 2: QUICK ACTION CARDS (Grid)
             ========================================== */}
        <div className="flow-quick-actions px-4 pb-6">
          <div className="grid grid-cols-2 gap-3 sm:gap-4 max-w-xl mx-auto">
            <QuickActionCard
              icon={Camera}
              title="Yemek Analizi"
              subtitle="Fotoğraf çek, makro/mikro hesapla"
              accent="emerald"
              onPress={handleNutritionPhoto}
              aria-label="Yemek fotoğrafı çekerek besin analizi başlat"
              showSparkle={true}
            />
            <QuickActionCard
              icon={Target}
              title="Form Analizi"
              subtitle="Fizik fotoğrafı, AI değerlendirmesi"
              accent="orange"
              onPress={handleFormPhoto}
              aria-label="Vücut form fotoğrafı yükleyerek analiz başlat"
              showSparkle={true}
            />
          </div>
        </div>

        {/* ==========================================
             SECTION 3: LIVE STATUS BAR (Compact)
             ========================================== */}
        <div className="flow-status-bar px-4 pb-4">
          <div className="grid grid-cols-3 gap-2 sm:gap-3 max-w-xl mx-auto">
            {/* Calorie Ring */}
            <StatusRing
              value={caloriePercent}
              label="Kalori"
              current={`${consumedCalories.toFixed(0)}`}
              target={`/ ${targetCalories.toFixed(0)} kcal`}
              color="orange"
              size={68}
              strokeWidth={5}
            />

            {/* Protein Ring */}
            <StatusRing
              value={proteinPercent}
              label="Protein"
              current={`${consumedProtein.toFixed(0)}g`}
              target={`/ ${targetProtein.toFixed(0)}g`}
              color="emerald"
              size={68}
              strokeWidth={5}
            />

            {/* Weight / Workout Status - tıklanınca Antrenman sekmesine götürür */}
            <button type="button" onClick={() => onNavigateTab && onNavigateTab('workout')} title="Antrenman sekmesine git"
              className="relative flex flex-col items-center justify-center p-3 bg-neutral-900/50 backdrop-blur-xl border border-neutral-800/50 rounded-2xl cursor-pointer hover:border-orange-500/40 transition-colors">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-10 h-10 rounded-xl bg-neutral-800/50 flex items-center justify-center">
                  {hasActiveProgram ? (
                    <Dumbbell className="w-5 h-5 text-orange-400" strokeWidth={2} />
                  ) : (
                    <Zap className="w-5 h-5 text-emerald-400" strokeWidth={2} />
                  )}
                </div>
              </div>
              <p className="text-xs font-mono text-neutral-500 uppercase tracking-wider">
                {hasActiveProgram ? 'Aktif Program' : 'Program Yok'}
              </p>
              <p className="text-base font-bold text-white font-mono mt-0.5">
                {todayWorkoutCount > 0 ? `${todayWorkoutCount} Set` : '—'}
              </p>
              <p className={`text-[10px] font-mono mt-1 text-center ${hasActiveProgram ? 'text-neutral-600' : 'text-orange-400 underline underline-offset-2'}`}>
                {hasActiveProgram ? 'Bugün tamamlanan' : 'Program oluştur →'}
              </p>
            </button>
          </div>
        </div>

        {/* ==========================================
             SECTION 4: TODAY'S FOCUS (Expandable)
             ========================================== */}
        {hasActiveProgram && (
          <TodayFocusSection
            workout={workout}
            onNavigate={() => onNavigateTab('workout')}
          />
        )}

        {/* ==========================================
             SECTION 5: QUICK INSIGHTS (If available)
             ========================================== */}
        {insights?.length > 0 && (
          <QuickInsightsSection
            insights={insights.slice(0, 2)}
            onViewAll={() => onNavigateTab('progress')}
          />
        )}

        {/* ==========================================
             SECTION 6: RECENT ACTIVITY (Compact)
             ========================================== */}
        {(metrics?.length > 0 || nutritionPlans?.length > 0) && (
          <RecentActivitySection
            metrics={metrics}
            nutrition={nutritionPlans}
          />
        )}

        {/* Bottom spacer for tab bar */}
        <div className="h-24" />
      </div>

    </div>
  );
}

/**
 * StatusRing - Circular progress indicator for macros
 */
function StatusRing({ value, label, current, target, color, size = 68, strokeWidth = 5 }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  const colors = {
    orange: { stroke: '#f97316', glow: 'rgba(249, 115, 22, 0.4)', bg: 'rgba(249, 115, 22, 0.1)' },
    emerald: { stroke: '#10b981', glow: 'rgba(16, 185, 129, 0.4)', bg: 'rgba(16, 185, 129, 0.1)' },
    blue: { stroke: '#3b82f6', glow: 'rgba(59, 130, 246, 0.4)', bg: 'rgba(59, 130, 246, 0.1)' },
  };

  const c = colors[color] || colors.orange;

  return (
    <div className="relative flex flex-col items-center justify-center p-3 bg-neutral-900/50 backdrop-blur-xl border border-neutral-800/50 rounded-2xl">
      <div className="relative" style={{ width: size, height: size }}>
        <svg viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#262626"
            strokeWidth={strokeWidth}
          />
          {/* Progress ring with glow */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={c.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
            filter="url(#ringGlow)"
          />
        </svg>
        <svg style={{ position: 'absolute', width: 0, height: 0 }}>
          <filter id="ringGlow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </svg>

        {/* Center content: only the value inside the ring */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-bold text-white font-mono leading-none">{current}</span>
        </div>
      </div>
      {/* Label & target below the ring — no overlap */}
      <p className="mt-1.5 text-[9px] font-mono uppercase tracking-wider leading-none" style={{ color: c.stroke }}>{label}</p>
      <p className="mt-0.5 text-[9px] font-mono text-neutral-500 leading-none whitespace-nowrap">{target}</p>
    </div>
  );
}

/**
 * TodayFocusSection - Shows today's workout focus compactly
 */
function TodayFocusSection({ workout, onNavigate }) {
  const today = new Date().getDay();
  const dayNames = ['Pazar', 'Pazartesi', 'Salı', 'Perşembe', 'Perşembe', 'Cuma', 'Cumartesi'];
  const todayName = dayNames[today];

  // Find today's workout or first available
  const todayProgram = workout?.programs?.find(p =>
    p.day_name?.toLowerCase().includes(todayName.toLowerCase())
  ) || workout?.programs?.[0];

  if (!todayProgram) return null;

  const exercises = todayProgram?.exercises?.slice(0, 3) || [];

  return (
    <div className="flow-today-focus px-4 pb-4">
      <button
        onClick={onNavigate}
        className="w-full max-w-xl mx-auto bg-neutral-900/60 backdrop-blur-xl border border-neutral-800/50 rounded-2xl p-4 transition-all duration-300 hover:border-orange-500/30 hover:shadow-[0_0_30px_-5px_rgba(249,115,22,0.2)] group"
        aria-label="Bugünün antrenman detaylarını gör"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-orange-500/10 flex items-center justify-center">
              <Dumbbell className="w-4 h-4 text-orange-400" strokeWidth={2} />
            </div>
            <div>
              <p className="text-xs font-mono text-neutral-500 uppercase tracking-wider">Bugün</p>
              <p className="font-medium text-white text-sm truncate max-w-[200px]">{todayProgram.day_name}</p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-neutral-500 group-hover:text-orange-400 transition-colors group-hover:translate-x-1" />
        </div>

        <div className="space-y-2">
          {exercises.map((ex, i) => (
            <div key={ex.id} className="flex items-center justify-between p-2.5 bg-neutral-950/50 rounded-xl border border-neutral-800/30 group-hover:border-neutral-700/50 transition-colors">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <span className="text-[10px] font-mono text-orange-400 w-5 text-center">{i + 1}.</span>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-white truncate">{ex.name}</p>
                  <p className="text-[10px] font-mono text-neutral-500">
                    {ex.target_sets}×{ex.target_reps} {ex.target_rpe ? `· RPE ${ex.target_rpe}` : ''}
                  </p>
                </div>
              </div>
              {ex.stretch_mediated && (
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  🎯 STRETCH
                </span>
              )}
            </div>
          ))}

          {todayProgram.exercises.length > 3 && (
            <p className="text-[10px] font-mono text-neutral-500 text-center py-1">
              +{todayProgram.exercises.length - 3} hareket daha...
            </p>
          )}
        </div>
      </button>
    </div>
  );
}

/**
 * QuickInsightsSection - Shows AI insights compactly
 */
function QuickInsightsSection({ insights, onViewAll }) {
  return (
    <div className="flow-insights px-4 pb-4">
      <div className="flex items-center justify-between px-1 mb-3">
        <p className="text-xs font-mono text-orange-500 uppercase tracking-wider">AI İçgörüleri</p>
        <button
          onClick={onViewAll}
          className="text-[10px] font-mono text-neutral-500 hover:text-orange-400 transition-colors flex items-center gap-1"
        >
          Tümü <ChevronRight className="w-3 h-3" />
        </button>
      </div>
      <div className="space-y-2 max-w-xl mx-auto">
        {insights.map((insight, i) => (
          <div
            key={insight.id || i}
            className="bg-neutral-900/60 backdrop-blur-xl border border-neutral-800/50 rounded-xl p-3 transition-all duration-300 hover:border-neutral-700/50"
          >
            <div className="flex items-start gap-2">
              <div className="w-7 h-7 rounded-xl bg-orange-500/10 flex items-center justify-center shrink-0 mt-0.5">
                <Sparkles className="w-3.5 h-3.5 text-orange-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-mono text-orange-400/80 uppercase tracking-wider mb-1">
                  {insight.category || 'ANALİZ'}
                </p>
                <p className="text-sm text-neutral-300 line-clamp-2 leading-relaxed">
                  {insight.content}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * RecentActivitySection - Shows recent weight/nutrition logs
 */
function RecentActivitySection({ metrics, nutrition }) {
  const latestWeight = metrics?.length > 0 ? metrics[metrics.length - 1] : null;
  const latestMeal = nutrition?.length > 0 ? nutrition[nutrition.length - 1] : null;

  return (
    <div className="flow-recent px-4 pb-6">
      <p className="text-xs font-mono text-orange-500 uppercase tracking-wider px-1 mb-3">Son Aktivite</p>
      <div className="grid grid-cols-2 gap-2 sm:gap-3 max-w-xl mx-auto">
        {latestWeight && (
          <div className="bg-neutral-900/60 backdrop-blur-xl border border-neutral-800/50 rounded-xl p-3 transition-all hover:border-neutral-700/50">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-7 h-7 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <BarChart2 className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <p className="text-xs font-mono text-neutral-500 uppercase tracking-wider">Kilo</p>
            </div>
            <p className="text-base font-bold text-white font-mono">{latestWeight.weight} kg</p>
            <p className="text-[10px] font-mono text-neutral-500">
              {new Date(latestWeight.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' })}
            </p>
          </div>
        )}

        {latestMeal && (
          <div className="bg-neutral-900/60 backdrop-blur-xl border border-neutral-800/50 rounded-xl p-3 transition-all hover:border-neutral-700/50">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-7 h-7 rounded-xl bg-orange-500/10 flex items-center justify-center">
                <UtensilsCrossed className="w-3.5 h-3.5 text-orange-400" strokeWidth={2} />
              </div>
              <p className="text-xs font-mono text-neutral-500 uppercase tracking-wider">Son Öğün</p>
            </div>
            <p className="text-sm font-medium text-white truncate">{latestMeal.meal_name}</p>
            <p className="text-[10px] font-mono text-neutral-500">
              {latestMeal.calories} kcal · {latestMeal.target_protein}g P
            </p>
          </div>
        )}

        {!latestWeight && !latestMeal && (
          <div className="col-span-2 bg-neutral-900/60 backdrop-blur-xl border border-neutral-800/50 rounded-xl p-6 text-center">
            <p className="text-sm text-neutral-500 font-mono">Henüz aktivite yok</p>
            <p className="text-[10px] text-neutral-600 mt-1">İlk antrenman veya öğün kaydını gir</p>
          </div>
        )}
      </div>
    </div>
  );
}

export { FlowScreen };