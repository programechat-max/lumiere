import { useState, useCallback } from 'react';
import { Send, Settings, LogOut, Square, ChevronRight } from 'lucide-react';

/**
 * FlowScreen - "Akış" ekranı (akışüst.png / akışalt.png birebir karşılığı)
 *
 * Yapı (mockup sırası):
 * 1. Header: LUMIERE COACHING + "31 Agu 2026 · 1. gün" + ayarlar & çıkış butonları
 * 2. Hero kart: "BUGÜNÜN ODAĞI" / "Pazartesi · Üst itişi" + kırmızı "Antrenmanı aç ›"
 *    + ilerleme çizgisi ve büyük "%" göstergesi
 * 3. Jarvis paneli: "LUMIERE YANINDA" / "Bugün nasıl hissediyorsun?" + giriş
 * 4. Günlük durum: KALORİ / PROTEİN / ANTRENMAN ring'leri
 * 5. HIZLI AKSİYONLAR: Yemek analizi + Video analizi kartları
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
}) {
  const [jarvisInput, setJarvisInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  // Quick Jarvis message handler → mesajı chat sekmesine taşı
  const handleJarvisSubmit = useCallback(
    async (e) => {
      e?.preventDefault?.();
      const message = jarvisInput.trim();
      if (!message || isProcessing) return;
      setIsProcessing(true);
      try {
        onSetChatMessage?.(message);
        onNavigateTab?.('chat');
        onQuickAction?.('chat', { message });
      } catch (error) {
        console.error('Jarvis navigation error:', error);
      } finally {
        setJarvisInput('');
        setIsProcessing(false);
      }
    },
    [jarvisInput, isProcessing, onNavigateTab, onSetChatMessage, onQuickAction]
  );

  // Hızlı aksiyonlar → ilgili sekmeye götür
  const handleNutritionPhoto = useCallback(() => {
    onQuickAction?.('nutrition-photo');
    onNavigateTab?.('nutrition');
  }, [onNavigateTab, onQuickAction]);

  const handleFormPhoto = useCallback(() => {
    onQuickAction?.('form-photo');
    onNavigateTab?.('workout');
  }, [onNavigateTab, onQuickAction]);

  const targetCalories = profile?.daily_calorie_target || 2200;
  const targetProtein = profile?.daily_protein_target || 140;
  const consumedCalories = (nutritionPlans || []).reduce((sum, plan) => sum + (plan.calories || 0), 0);
  const consumedProtein = (nutritionPlans || []).reduce((sum, plan) => sum + (plan.target_protein || 0), 0);

  const hasActiveProgram = workout?.programs?.length > 0;
  const todayWorkoutCount = workout?.today_logs?.length || 0;
  const dayNames = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi'];
  const todayName = dayNames[new Date().getDay()];
  const heroProgram =
    workout?.programs?.find((program) =>
      program.day_name?.toLocaleLowerCase('tr-TR').includes(todayName.toLocaleLowerCase('tr-TR'))
    ) || workout?.programs?.[0];
  const heroExerciseCount = heroProgram?.exercises?.length || 0;
  const heroProgress =
    heroExerciseCount > 0 ? Math.min(Math.round((todayWorkoutCount / heroExerciseCount) * 100), 100) : 0;
  const focusText = heroProgram?.focus
    ? heroProgram.focus.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
    : '';
  const heroTitle = heroProgram?.day_name
    ? `${heroProgram.day_name} · ${focusText || 'Üst itiş'}`
    : 'Pazartesi · Üst itiş\n(Göğüs / Omuz)';

  return (
    <div className="min-h-0">
      {/* 1. HEADER - marka + üyelik + ayarlar/çıkış (mockup akışüst) */}
      <header
        className="lp-phone-header"
        style={{ paddingTop: 'calc(env(safe-area-inset-top, 0px) + 18px * var(--lp-scale))' }}
      >
        <div className="lp-brand">
          <div className="lp-brand-mark">
            <Square strokeWidth={2.5} style={{ width: 'calc(18px * var(--lp-scale))', height: 'calc(18px * var(--lp-scale))' }} />
          </div>
          <div className="min-w-0">
            <div className="lp-brand-name">
              LUMIERE <b>COACHING</b>
            </div>
            <div className="lp-member-since">{memberSinceLabel || '31 Ağu 2026 · 1. gün'}</div>
          </div>
        </div>
        <div className="lp-header-actions">
          <button type="button" className="lp-icon-button" aria-label="Ayarlar" onClick={() => onOpenSettings?.()}>
            <Settings strokeWidth={2.25} style={{ width: 'calc(16px * var(--lp-scale))', height: 'calc(16px * var(--lp-scale))' }} />
          </button>
          <button type="button" className="lp-icon-button" aria-label="Çıkış yap" onClick={() => onLogout?.()}>
            <LogOut strokeWidth={2.25} style={{ width: 'calc(16px * var(--lp-scale))', height: 'calc(16px * var(--lp-scale))' }} />
          </button>
        </div>
      </header>

      {/* 2. HERO - kırmızı gradyan kart + kırmızı buton (mockup akışüst) */}
      <section className="lp-hero">
        <p className="lp-section-kicker">Bugünün odağı</p>
        <h2 style={{ whiteSpace: 'pre-line' }}>{heroTitle}</h2>
        <p>
          {hasActiveProgram
            ? `${heroExerciseCount} egzersizle bugün gücünü ve hareket kaliteni geliştir.`
            : '5 egzersizle bugün gücünü ve hareket kaliteni geliştir.'}
        </p>
        <button type="button" onClick={() => onNavigateTab?.('workout')} className="lp-primary">
          Antrenmanı aç <ChevronRight strokeWidth={2.5} />
        </button>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'calc(10px * var(--lp-scale))',
            marginTop: 'calc(14px * var(--lp-scale))',
          }}
        >
          <div className="lp-progress-line" style={{ flex: 1 }}>
            <b style={{ width: `${heroProgress}%` }} />
          </div>
          <strong style={{ fontSize: 'calc(13px * var(--lp-scale))', fontWeight: 900, letterSpacing: '-0.04em' }}>
            {heroProgress}%
          </strong>
        </div>
      </section>

      {/* 3. LUMIERE YANINDA - Jarvis giriş paneli */}
      <section className="lp-panel" style={{ marginTop: 'calc(12px * var(--lp-scale))' }}>
        <div className="lp-panel-heading">
          <div className="min-w-0">
            <p className="lp-section-kicker">Lumiere yanında</p>
            <strong className="block mt-0.5">Bugün nasıl hissediyorsun?</strong>
          </div>
          <span>✦</span>
        </div>
        <form onSubmit={handleJarvisSubmit} className="lp-jarvis-input">
          <input
            type="text"
            value={jarvisInput}
            onChange={(e) => setJarvisInput(e.target.value)}
            placeholder="Lumiere'e bir şey sor..."
            disabled={isProcessing}
            className="flex-1 min-w-0 bg-transparent border-0 focus:outline-none text-neutral-100 placeholder:text-[#656571] disabled:opacity-50"
            style={{ fontSize: 'calc(11px * var(--lp-scale))' }}
          />
          <button type="submit" className="lp-send" aria-label="Gönder" disabled={isProcessing || !jarvisInput.trim()}>
            <Send strokeWidth={2.5} style={{ width: 'calc(14px * var(--lp-scale))', height: 'calc(14px * var(--lp-scale))' }} />
          </button>
        </form>
      </section>

      {/* 4. GÜNLÜK DURUM - ring'li statlar (KALORİ / PROTEİN / ANTRENMAN) */}
      <section className="lp-panel">
        <div className="lp-panel-heading">
          <div className="min-w-0">
            <p className="lp-section-kicker">Günlük durum</p>
            <strong className="block mt-0.5">Vücudunu dinle.</strong>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab?.('nutrition')}
            className="shrink-0 transition-opacity hover:opacity-80"
            style={{ color: 'var(--lp-red-2)', fontSize: 'calc(10px * var(--lp-scale))', fontWeight: 700 }}
          >
            Detaylar ›
          </button>
        </div>
        <div className="lp-stats">
          <div className="lp-stat">
            <div className="lp-ring red">{consumedCalories.toFixed(0)}</div>
            <label>Kalori</label>
            <div className="lp-small lp-muted">/ {targetCalories} kcal</div>
          </div>
          <div className="lp-stat">
            <div className="lp-ring green">{consumedProtein.toFixed(0)}g</div>
            <label>Protein</label>
            <div className="lp-small lp-muted">/ {targetProtein}g</div>
          </div>
          <button type="button" onClick={() => onNavigateTab?.('workout')} className="lp-stat" aria-label="Antrenman sekmesine git">
            <div className="lp-ring">+</div>
            <label>Antrenman</label>
            <div className="lp-small lp-muted">
              {hasActiveProgram ? (todayWorkoutCount > 0 ? `${todayWorkoutCount} set` : 'Hazır') : 'Oluştur ›'}
            </div>
          </button>
        </div>
      </section>

      {/* 5. HIZLI AKSİYONLAR (mockup akışalt) */}
      <p className="lp-section-kicker" style={{ margin: 'calc(17px * var(--lp-scale)) 2px calc(8px * var(--lp-scale))' }}>
        Hızlı aksiyonlar
      </p>
      <div className="lp-quick-grid">
        <button
          type="button"
          className="lp-quick green"
          onClick={handleNutritionPhoto}
          aria-label="Yemek analizi"
        >
          <span className="lp-quick-icon">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="4" />
              <rect x="8" y="8" width="8" height="8" rx="1.5" />
            </svg>
          </span>
          <strong>Yemek analizi</strong>
          <p>Fotoğraftan makro ve kalori</p>
        </button>
        <button
          type="button"
          className="lp-quick"
          onClick={handleFormPhoto}
          aria-label="Video analizi"
        >
          <span className="lp-quick-icon">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="9" />
              <circle cx="12" cy="12" r="5" />
              <circle cx="12" cy="12" r="1.5" fill="currentColor" />
            </svg>
          </span>
          <strong>Video analizi</strong>
          <p>Postür, kas dengesi, hareket</p>
        </button>
      </div>
    </div>
  );
}
