import { useCallback, useEffect, useRef, useState } from 'react';
import { Settings2 } from 'lucide-react';
import { BottomNav, Logo, NAV_ORDER } from './components/chrome';
import { LoginScreen, RegisterScreen, OnboardingScreen } from './components/Auth';
import { FlowScreen, DailyScreen } from './components/FlowDaily';
import { WorkoutScreen } from './components/Workout';
import { NutritionScreen } from './components/Nutrition';
import { CoachScreen, ProgressScreen } from './components/CoachProgress';
import { SettingsSheet } from './components/Settings';
import { ProgramCreator } from './components/ProgramCreator';
import { MorningCheckIn } from './components/MorningCheckIn';
import { useLumiereStore } from './lib/store';
import { todayISO } from './lib/utils';
import * as authService from './services/authService';
import type { TabKey } from './lib/types';

type Page = 'login' | 'register' | 'onboard' | 'creator' | 'app';

export default function App() {
  const store = useLumiereStore();
  const [page, setPage] = useState<Page>(() => {
    if (!authService.isAuthenticated()) return 'login';
    return store.onboarded ? 'app' : 'onboard';
  });
  const [tab, setTab] = useState<TabKey>('flow');
  const [dir, setDir] = useState<'right' | 'left'>('right');
  const [settings, setSettings] = useState(false);
  const [checkinOpen, setCheckinOpen] = useState(false);
  const tabRef = useRef<TabKey>('flow');
  const touchRef = useRef<{ x: number; y: number } | null>(null);

  // Oturum süresi dolduğunda (401 yenileme başarısız) login'e dön.
  useEffect(() => {
    const onExpired = () => setPage('login');
    window.addEventListener('lumiere:session-expired', onExpired);
    return () => window.removeEventListener('lumiere:session-expired', onExpired);
  }, []);

  // Günlük check-in: günün ilk açılışında (saate bakılmaksızın) otomatik sor.
  // Hesap yeni açıldığında da sorulması için 04:00-14:00 kısıtı kaldırıldı;
  // kullanıcı "Şimdi değil" derse gün 'snoozed' işaretlenir, akışta kart kalır.
  useEffect(() => {
    if (page !== 'app') return;
    if (store.checkinMap[todayISO()]) return;
    setCheckinOpen(true);
  }, [page]);

  const navigate = useCallback((next: TabKey) => {
    const prev = tabRef.current;
    if (prev === next) return;
    const pi = NAV_ORDER.indexOf(prev);
    const ni = NAV_ORDER.indexOf(next);
    setDir(ni > pi ? 'right' : 'left');
    tabRef.current = next;
    setTab(next);
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
  }, [tab, page]);

  const onTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    touchRef.current = { x: t.clientX, y: t.clientY };
  };
  const onTouchEnd = (e: React.TouchEvent) => {
    const s = touchRef.current;
    touchRef.current = null;
    if (!s) return;
    const el = e.target as HTMLElement | null;
    if (el?.closest?.('.no-scrollbar, input, textarea')) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - s.x;
    const dy = t.clientY - s.y;
    if (Math.abs(dx) < 70 || Math.abs(dx) < Math.abs(dy) * 1.6) return;
    const idx = NAV_ORDER.indexOf(tabRef.current);
    const next = dx < 0 ? NAV_ORDER[idx + 1] : NAV_ORDER[idx - 1];
    if (next) navigate(next);
  };

  if (page === 'login') return <LoginScreen store={store} go={(p) => setPage(p === 'app' ? (store.onboarded ? 'app' : 'onboard') : 'register')} />;
  if (page === 'register') return <RegisterScreen store={store} go={(p) => setPage(p === 'onboard' ? 'onboard' : 'login')} />;
  if (page === 'onboard') return <OnboardingScreen store={store} done={() => setPage('creator')} />;
  if (page === 'creator') return <ProgramCreator store={store} done={() => { setTab('flow'); tabRef.current = 'flow'; setPage('app'); }} />;

  return (
    <div className="min-h-dvh bg-[#f4f1ec] text-[#1c1512]" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-28 left-1/2 h-72 w-[540px] -translate-x-1/2 rounded-full bg-[#d92835]/10 blur-[100px]" />
      </div>
      <div className="relative mx-auto min-h-dvh w-full max-w-md px-5 pb-32">
        {/* top brand bar */}
        <div className="flex items-center justify-between pt-[max(1.25rem,env(safe-area-inset-top))]">
          <Logo />
          <span className="rounded-full bg-[#1c1512] px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-widest text-white">
            {store.profile.streak} günlük seri
          </span>
        </div>
        <div key={tab} className={dir === 'left' ? 'page-in-left mt-4' : 'page-in-right mt-4'}>
          {tab === 'flow' && <FlowScreen store={store} go={navigate} onOpenCheckIn={() => setCheckinOpen(true)} />}
          {tab === 'coach' && <CoachScreen store={store} />}
          {tab === 'daily' && <DailyScreen store={store} />}
          {tab === 'workout' && <WorkoutScreen store={store} />}
          {tab === 'nutrition' && <NutritionScreen store={store} />}
          {tab === 'progress' && <ProgressScreen store={store} />}
        </div>
        {/* settings shortcut handled inside headers? global fallback */}
        <button
          onClick={() => setSettings(true)}
          className="sr-only"
          aria-hidden
          tabIndex={-1}
        >
          ayarlar
        </button>
        <SettingsSheet store={store} open={settings} onClose={() => setSettings(false)} onLogout={() => { setPage('login'); setSettings(false); }} />
        {checkinOpen && (
          <MorningCheckIn store={store} onDone={() => setCheckinOpen(false)} />
        )}
      </div>
      <BottomNav active={tab} onNavigate={navigate} />
      {/* floating settings access: long-press free — visible gear above nav on inner pages */}
      <button
        onClick={() => setSettings(true)}
        aria-label="Ayarlar"
        className="fixed bottom-[104px] right-[max(1rem,calc(50%-13.5rem))] z-40 grid h-12 w-12 place-items-center rounded-full border border-[#e7ddcf] bg-white/95 text-[#6f6259] shadow-[0_14px_30px_-14px_rgba(60,32,28,0.45)] backdrop-blur transition active:scale-90"
      >
        <Settings2 size={19} />
      </button>
    </div>
  );
}
