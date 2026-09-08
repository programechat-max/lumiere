import { useState, useEffect, useCallback, useRef } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, CartesianGrid,
} from 'recharts';
import {
  Radar, MessageCircle, Calendar, Dumbbell, UtensilsCrossed, TrendingUp, Activity,
  LogOut, Cpu, Send, Settings, Square,
} from 'lucide-react';
import Login from './Login';
import Register from './Register';
import FlowScreen from './components/FlowScreen';
import SettingsMenu from './components/SettingsMenu';
import OnboardingWizard from './components/OnboardingWizard';
import ProgramBuilder from './components/ProgramBuilder';
import AdminPanel from './components/AdminPanel';
import { API_BASE } from './config';
import * as authService from './services/authService';



const DATA_MUTATING_INTENTS = new Set([
  'log_food', 'complete_all_meals', 'log_workout', 'log_weight',
  'remember', 'forget', 'modify_meal_plan', 'delete_meal_plan',
  'delete_food_log', 'modify_workout_program', 'delete_workout_program',
  'daily_checkin',
]);

// Header'da "üyelik başlangıcı"nı gösterirken kullanılır - örn. "15 Ağu 2026'dan beri · 12. gün"
function formatMemberSince(isoDate) {
  try {
    const start = new Date(isoDate);
    if (Number.isNaN(start.getTime())) return null;
    const dayCount = Math.max(Math.floor((Date.now() - start.getTime()) / 86400000) + 1, 1);
    const dateLabel = start.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short', year: 'numeric' });
    return `${dateLabel} · ${dayCount}. gün`;
  } catch {
    return null;
  }
}

const NAV_ITEMS = [
  { key: 'flow', label: 'AKIŞ', Icon: Radar },
  { key: 'chat', label: 'LUMIERE', Icon: MessageCircle },
  { key: 'daily', label: 'GÜNLÜK', Icon: Calendar },
  { key: 'workout', label: 'ANTRENMAN', Icon: Dumbbell },
  { key: 'nutrition', label: 'MUTFAK', Icon: UtensilsCrossed },
  { key: 'progress', label: 'GELİŞİM', Icon: TrendingUp },
];
const NAV_KEYS = NAV_ITEMS.map(({ key }) => key);

// Günlük ekran başlığındaki tarih etiketi - örn. "31 Ağustos Pazartesi"
function formatDailyDate(iso) {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', weekday: 'long' });
  } catch {
    return iso;
  }
}

export default function DashboardMaster() {
  // Kullanıcının programı kullanmaya başladığı tarih (kayıt tarihi) - başlıkta gösterilir.
  const [memberSince, setMemberSince] = useState(() => {
    try {
      const stored = authService.getStoredUser();
      return stored?.created_at || null;
    } catch {
      return null;
    }
  });
  const [currentPage, setCurrentPage] = useState(() => {
    const path = window.location.pathname;
    if (path === '/login') return 'login';
    if (path === '/register') return 'register';
    return authService.isAuthenticated() ? 'dashboard' : 'login';
  });
  const [isSetupComplete, setIsSetupComplete] = useState(false);
  // Onboarding bittikten sonra açılan Program Oluşturucu (detaylı anketler) ekranı
  const [showProgramBuilder, setShowProgramBuilder] = useState(false);
  const [programContext, setProgramContext] = useState(null);
  // Token varsa /api/status doğrulanana kadar "yükleniyor" göstermemiz gerekiyor;
  // aksi halde isSetupComplete henüz bilinmeden (varsayılan false) bir anlığına
  // yanlışlıkla onboarding ekranı gösterilir. Token yoksa zaten login'e düşülüyor.
  const [loading, setLoading] = useState(authService.isAuthenticated());
  const [activeTab, setActiveTab] = useState('flow');
  const [tabDirection, setTabDirection] = useState(1);
  const activeTabRef = useRef('flow');
  const swipeStartRef = useRef(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  // Kamera/mikrofon için kullanıcının kalıcı rıza kararı (/api/status'tan gelir).
  // null => hiç sorulmadı, true => verdi, false => reddetti.
  const [permissions, setPermissions] = useState({ camera: null, microphone: null });

  const [profile, setProfile] = useState(null);
  const [nutritionPlans, setNutritionPlans] = useState([]);
  const [workout, setWorkout] = useState({ programs: [], today_logs: [] });
  const [metrics, setMetrics] = useState([]);
  const [insights, setInsights] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [weightInput, setWeightInput] = useState('');
  const [savingWeight, setSavingWeight] = useState(false);
  const [mealPlan, setMealPlan] = useState([]);
  const [deloadStatus, setDeloadStatus] = useState(null);
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [dailyNutrition, setDailyNutrition] = useState(null);
  const [dailyWorkout, setDailyWorkout] = useState(null);
  const [dailyHeatmap, setDailyHeatmap] = useState({});
  const [loadingDaily, setLoadingDaily] = useState(false);
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [generatingProgram, setGeneratingProgram] = useState(false);
  const [workoutError, setWorkoutError] = useState('');

  // Sprint 1: Jarvis chat
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatSending, setChatSending] = useState(false);
  const chatEndRef = useRef(null);

  // Sprint 1: Gelişim grafikleri
  const [chartData, setChartData] = useState(null);
  const [loadingCharts, setLoadingCharts] = useState(false);

  // Sprint 1: Yemek fotoğrafı
  const [foodPhotoPreview, setFoodPhotoPreview] = useState(null);
  const [foodPhotoAnalyzing, setFoodPhotoAnalyzing] = useState(false);
  const [foodPhotoError, setFoodPhotoError] = useState('');
  const foodPhotoInputRef = useRef(null);

  const [statusError, setStatusError] = useState('');
  const isAdmin = ['ADMIN', 'SUPER_ADMIN'].includes((authService.getStoredUser()?.role || '').toUpperCase());

  const navigateToTab = useCallback((nextTab) => {
    if (!NAV_KEYS.includes(nextTab)) return;
    const previousTab = activeTabRef.current;
    if (previousTab === nextTab) return;
    const previousIndex = NAV_KEYS.indexOf(previousTab);
    const nextIndex = NAV_KEYS.indexOf(nextTab);
    setTabDirection(nextIndex >= previousIndex ? 1 : -1);
    activeTabRef.current = nextTab;
    setActiveTab(nextTab);
  }, []);

  const handleTabTouchStart = useCallback((event) => {
    if (event.touches.length !== 1) return;
    const target = event.target;
    if (target instanceof Element && target.closest('button, input, textarea, select, a, [data-no-swipe]')) {
      swipeStartRef.current = null;
      return;
    }
    const touch = event.touches[0];
    swipeStartRef.current = { x: touch.clientX, y: touch.clientY, time: Date.now() };
  }, []);

  const handleTabTouchEnd = useCallback((event) => {
    const start = swipeStartRef.current;
    swipeStartRef.current = null;
    if (!start || event.changedTouches.length !== 1) return;
    const touch = event.changedTouches[0];
    const deltaX = touch.clientX - start.x;
    const deltaY = touch.clientY - start.y;
    const elapsed = Date.now() - start.time;
    if (elapsed > 850 || Math.abs(deltaX) < 56 || Math.abs(deltaX) < Math.abs(deltaY) * 1.25) return;

    const currentIndex = NAV_KEYS.indexOf(activeTabRef.current);
    const nextIndex = deltaX < 0
      ? Math.min(currentIndex + 1, NAV_KEYS.length - 1)
      : Math.max(currentIndex - 1, 0);
    if (nextIndex !== currentIndex) navigateToTab(NAV_KEYS[nextIndex]);
  }, [navigateToTab]);

  // Her sekme yeni bir ekran gibi en üstten başlar; özellikle iPhone'da uzun
  // bir akıştan sonra sekme değiştirilince eski scroll konumu taşınmaz.
  useEffect(() => {
    if (!isSetupComplete || showProgramBuilder) return;
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }, [activeTab, isSetupComplete, showProgramBuilder]);

  // Auth helpers (component içinde tanımlanmış)
  const handleLogout = () => {
    // authService.logout() sunucudaki refresh-token oturumunu da iptal eder
    // (HttpOnly cookie temizlenir); yanıtı beklemeden yerel oturumu hemen temizleyip
    // yönlendiriyoruz ki çıkış kullanıcıya anında yansısın.
    authService.logout().catch(() => {});
    setCurrentPage('login');
  };

  // Token geçersiz/süresi dolmuşsa (401) oturumu temizleyip login'e at - aksi halde
  // uygulama "kurulum tamamlanmamış" sanıp yanlışlıkla onboarding ekranını gösterir.
  const handleIfSessionExpired = useCallback((res) => {
    if (res.status === 401) {
      authService.clearLocalSession();
      setCurrentPage('login');
      return true;
    }
    return false;
  }, [setCurrentPage]);

  const authenticatedFetch = useCallback(async (url, options = {}) => {
    const token = authService.getAccessToken();
    if (!token) {
      return Promise.reject(new Error('No token'));
    }
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
      },
    });
  }, []);

  // Quick action handler for FlowScreen cross-tab communication
  const handleQuickAction = useCallback((action, payload) => {
    console.log('[FlowScreen] Quick action:', action, payload);
    // This can be extended to trigger specific behaviors
    // For now, the navigation is handled within FlowScreen via navigate()
  }, []);

  // ==========================================
  // BACKEND'DEN VERİLERİ ÇEKEN MOTOR
  // ==========================================
  const fetchDashboardData = useCallback(async () => {
    const token = authService.getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      console.log('[Dashboard] Fetching status...');
      const statusCtrl = new AbortController();
      const statusTimer = setTimeout(() => statusCtrl.abort(), 30_000);
      let statusRes;
      try {
        statusRes = await fetch(`${API_BASE}/api/status`, {
          headers: { 'Authorization': `Bearer ${token}` },
          signal: statusCtrl.signal,
        });
      } finally {
        clearTimeout(statusTimer);
      }

      if (handleIfSessionExpired(statusRes)) return;

      if (!statusRes.ok) {
        // Backend bağlantısı var ama hata kodu döndü - belki 401, 500
        const errText = await statusRes.text().catch(() => '');
        console.error('[Dashboard] Status error:', statusRes.status, errText);

        if (statusRes.status === 401) {
          // Token geçersiz
          handleIfSessionExpired(statusRes);
        } else {
          // Diğer hatalar - onboarding'e gönder (yeni kullanıcı olabilir)
          setIsSetupComplete(false);
          setStatusError('');
        }
        return;
      }
      setStatusError('');

      const statusData = await statusRes.json();
      console.log('[Dashboard] Status data:', statusData);
      setIsSetupComplete(!!statusData.is_setup_complete);
      setPermissions({
        camera: statusData.camera_permission_granted ?? null,
        microphone: statusData.microphone_permission_granted ?? null,
      });

      if (statusData.is_setup_complete) {
        console.log('[Dashboard] Fetching full dashboard data...');
        const [profileRes, nutritionRes, workoutRes, metricsRes, insightsRes, mealPlanRes, deloadRes] = await Promise.all([
          fetch(`${API_BASE}/api/profile`, { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch(`${API_BASE}/api/nutrition`, { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch(`${API_BASE}/api/workout`, { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch(`${API_BASE}/api/metrics?days=30`, { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch(`${API_BASE}/api/insights`, { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch(`${API_BASE}/api/mealplan`, { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch(`${API_BASE}/api/workout/deload`, { headers: { 'Authorization': `Bearer ${token}` } }),
        ]);
        setProfile(await profileRes.json());
        setNutritionPlans(await nutritionRes.json());
        setWorkout(await workoutRes.json());
        setMetrics(await metricsRes.json());
        setInsights(await insightsRes.json());
        setMealPlan(await mealPlanRes.json());
        setDeloadStatus(await deloadRes.json());
      }
    } catch (error) {
      console.error("[Dashboard] Backend bağlantı hatası:", error);
      // Network hatası - onboarding'e düş ama hata göster
      setIsSetupComplete(false);
      setStatusError('Sunucuya bağlanılamadı. Backend çalışıyor mu kontrol eder misin?');
    } finally {
      setLoading(false);
    }
  }, [handleIfSessionExpired]);

  // Kayıt tarihi (memberSince) localStorage'da yoksa (eski hesaplarda olabilir) /api/auth/me'den tazele.
  useEffect(() => {
    if (memberSince || currentPage !== 'dashboard') return;
    const token = authService.getAccessToken();
    if (!token) return;
    fetch(`${API_BASE}/api/auth/me`, { headers: { 'Authorization': `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : null))
      .then((me) => {
        if (!me) return;
        setMemberSince(me.created_at);
        const stored = authService.getStoredUser() || {};
        localStorage.setItem('user', JSON.stringify({ ...stored, created_at: me.created_at }));
      })
      .catch(() => {});
  }, [memberSince, currentPage]);

  useEffect(() => {
    if (currentPage !== 'dashboard') return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000);    return () => clearInterval(interval);
  }, [fetchDashboardData, currentPage]);

  const fetchDailyWindow = useCallback(async (dateStr) => {
    setLoadingDaily(true);
    try {
      const [nutritionRes, workoutRes, heatmapRes] = await Promise.all([
        authenticatedFetch(`${API_BASE}/api/nutrition/day?day=${dateStr}`),
        authenticatedFetch(`${API_BASE}/api/workout/day?day=${dateStr}`),
        authenticatedFetch(`${API_BASE}/api/workout/heatmap/day?day=${dateStr}`),
      ]);
      setDailyNutrition(await nutritionRes.json());
      setDailyWorkout(await workoutRes.json());
      setDailyHeatmap(await heatmapRes.json());
    } catch (error) {
      console.error("Günlük pencere hatası:", error);
    } finally {
      setLoadingDaily(false);
    }
  }, [authenticatedFetch]);

  useEffect(() => {
    if (activeTab === 'daily') {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchDailyWindow(selectedDate);
    }
  }, [activeTab, selectedDate, fetchDailyWindow]);

  const fetchChartData = useCallback(async () => {
    setLoadingCharts(true);
    try {
      const res = await authenticatedFetch(`${API_BASE}/api/progress/charts`);
      setChartData(await res.json());
    } catch (e) {
      console.error('Grafik verisi alınamadı:', e);
    } finally {
      setLoadingCharts(false);
    }
  }, [authenticatedFetch]);

  useEffect(() => {
    if (activeTab === 'progress') {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchChartData();
    }
  }, [activeTab, fetchChartData]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const fetchJarvisContext = useCallback(async () => {
    try {
      const historyRes = await authenticatedFetch(`${API_BASE}/api/chat/history?limit=40`);
      const history = await historyRes.json();
      if (history.length > 0) {
        setChatMessages(history.map((m) => ({ role: m.role, text: m.text, intent: m.intent })));
      } else {
        setChatMessages([{ role: 'jarvis', text: 'Merhaba efendim. Beslenme, antrenman veya hedefleriniz hakkında bana yazabilirsiniz.' }]);
      }
    } catch (e) {
      console.error('Jarvis context yüklenemedi:', e);
    }
  }, [authenticatedFetch]);

  useEffect(() => {
    if (activeTab === 'chat' && isSetupComplete) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchJarvisContext();
    }
  }, [activeTab, isSetupComplete, fetchJarvisContext]);

  const sendChatMessage = async (e, overrideText) => {
    e?.preventDefault();
    const text = (overrideText ?? chatInput).trim();
    if (!text || chatSending) return;
    setChatInput('');
    setChatMessages((prev) => [...prev, { role: 'user', text }]);
    setChatSending(true);
    try {
      const res = await authenticatedFetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error('chat failed');
      const data = await res.json();
      setChatMessages((prev) => [...prev, {
        role: 'jarvis',
        text: data.jarvis_reply,
        intent: data.intent,
        enriched: data.enriched,
        trainingAdvice: data.training_advice,
      }]);
      if (DATA_MUTATING_INTENTS.has(data.intent)) {
        fetchDashboardData();
        if (activeTab === 'progress') fetchChartData();
        fetchJarvisContext();
      }
    } catch (err) {
      console.error(err);
      setChatMessages((prev) => [...prev, { role: 'jarvis', text: 'Bağlantı hatası efendim, Lumiere bağlantısını kontrol eder misiniz?' }]);
    } finally {
      setChatSending(false);
    }
  };

  const analyzeFoodPhoto = async (file) => {
    if (!file) return;
    setFoodPhotoError('');
    setFoodPhotoAnalyzing(true);
    setFoodPhotoPreview(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await authenticatedFetch(`${API_BASE}/api/nutrition/photo`, { method: 'POST', body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Analiz başarısız');
      }
      const result = await res.json();
      if (result.photo_type === 'food' && result.food) {
        setFoodPhotoPreview({ ...result.food, previewUrl: URL.createObjectURL(file) });
      } else if (result.photo_type === 'physique' && result.physique) {
        setFoodPhotoError('Bu bir yemek fotoğrafı değil — vücut/fizik fotoğrafı algılandı. Yemek tabağının fotoğrafını yükleyin.');
      } else {
        setFoodPhotoError(result.clarify_message || 'Yemek tanımlanamadı, daha net bir fotoğraf dener misiniz?');
      }
    } catch (err) {
      setFoodPhotoError(err.message || 'Fotoğraf analiz edilemedi.');
    } finally {
      setFoodPhotoAnalyzing(false);
    }
  };

  const confirmFoodPhoto = async () => {
    if (!foodPhotoPreview) return;
    try {
      await authenticatedFetch(`${API_BASE}/api/nutrition/photo/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          meal_name: foodPhotoPreview.meal_name || 'Öğün',
          ingredients: foodPhotoPreview.description || '',
          calories: foodPhotoPreview.calories || 0,
          protein: foodPhotoPreview.protein || 0,
          carbs: foodPhotoPreview.carbs || 0,
          fats: foodPhotoPreview.fats || 0,
        }),
      });
      setFoodPhotoPreview(null);
      fetchDashboardData();
    } catch (e) {
      console.error(e);
      setFoodPhotoError('Kayıt sırasında hata oluştu.');
    }
  };

  const shiftSelectedDate = (deltaDays) => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + deltaDays);
    setSelectedDate(d.toISOString().split('T')[0]);
  };

  const runWeeklyAnalysis = async () => {
    setAnalyzing(true);
    try {
      await authenticatedFetch(`${API_BASE}/api/insights/generate`, { method: 'POST' });
      const res = await authenticatedFetch(`${API_BASE}/api/insights`);
      setInsights(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setAnalyzing(false);
    }
  };

  const submitWeight = async (e) => {
    e.preventDefault();
    if (!weightInput) return;
    setSavingWeight(true);
    try {
      await authenticatedFetch(`${API_BASE}/api/metrics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weight: parseFloat(weightInput) }),
      });
      setWeightInput('');
      const res = await authenticatedFetch(`${API_BASE}/api/metrics?days=30`);
      setMetrics(await res.json());
      fetchChartData();
    } catch (e) {
      console.error(e);
    } finally {
      setSavingWeight(false);
    }
  };

  const regenerateMealPlan = async () => {
    setGeneratingPlan(true);
    try {
      const res = await authenticatedFetch(`${API_BASE}/api/mealplan/generate`, { method: 'POST' });
      setMealPlan(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setGeneratingPlan(false);
    }
  };

  const deleteMealPlan = async () => {
    try {
      await authenticatedFetch(`${API_BASE}/api/mealplan`, { method: 'DELETE' });
      setMealPlan([]);
    } catch (e) {
      console.error(e);
    }
  };

  const generateWorkoutProgram = async () => {
    setGeneratingProgram(true);
    setWorkoutError('');
    try {
      // AI üretimi 1-2 dakika sürebilir; hata varsa kullanıcıya görünür şekilde bildir
      const res = await authenticatedFetch(`${API_BASE}/api/workout/program/generate`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = typeof data.detail === 'string' ? data.detail : 'AI programı oluşturamadı';
        throw new Error(detail);
      }
      if (!Array.isArray(data) || data.length === 0) {
        throw new Error('AI bu denemede program üretemedi, lütfen tekrar dene.');
      }
      const workoutRes = await authenticatedFetch(`${API_BASE}/api/workout`);
      setWorkout(await workoutRes.json());
    } catch (e) {
      console.error(e);
      setWorkoutError(e?.message || 'Program oluşturulamadı, tekrar dener misin?');
    } finally {
      setGeneratingProgram(false);
    }
  };

  // Hedefler artık backend'deki profilden geliyor - sabit değil
  const targetCalories = profile?.daily_calorie_target || 2200;
  const targetProtein = profile?.daily_protein_target || 140;
  const targetCarbs = profile?.daily_carb_target || 220;

  const consumedCalories = nutritionPlans.reduce((acc, plan) => acc + (plan.calories || 0), 0);
  const consumedProtein = nutritionPlans.reduce((acc, plan) => acc + (plan.target_protein || 0), 0);
  const consumedCarbs = nutritionPlans.reduce((acc, plan) => acc + (plan.target_carbs || 0), 0);

  const caloriePercent = targetCalories > 0 ? (consumedCalories / targetCalories) : 0;
  const dashOffset = 2 * Math.PI * 50 - (Math.min(caloriePercent, 1)) * (2 * Math.PI * 50);

  const latestWeight = metrics.length > 0 ? metrics[metrics.length - 1].weight : profile?.current_weight;
  const firstWeight = metrics.find(m => m.weight)?.weight;
  const weightDelta = (latestWeight && firstWeight) ? (latestWeight - firstWeight) : null;

  // ==========================================
  // AUTH SAYFALARI
  // ==========================================
  if (currentPage === 'login') {
    return <Login setCurrentPage={setCurrentPage} />;
  }
  if (currentPage === 'register') {
    return <Register setCurrentPage={setCurrentPage} />;
  }

  if (loading) {
    return (
      <div className="lumiere-app-shell text-white flex min-h-screen flex-col items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 auth-grid-bg pointer-events-none opacity-60" />
        <div className="absolute w-72 h-72 rounded-full bg-red-500/20 blur-3xl auth-glow-orb pointer-events-none" />
        <div className="relative flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-neutral-800 border-t-red-500 rounded-full animate-spin" />
          <p className="text-sm tracking-[0.16em] text-neutral-400 uppercase font-semibold">
            LUMIERE <span className="text-red-400">COACHING</span> hazırlanıyor
          </p>
        </div>
      </div>
    );
  }

  // ==========================================
  // BAĞLANTI HATASI (durum bilinmiyor - onboarding'e YANLIŞLIKLA düşmeyelim)
  // ==========================================
  if (statusError) {
    return (
      <div className="lumiere-app-shell text-white flex min-h-screen flex-col items-center justify-center relative overflow-hidden p-6 text-center">
        <div className="absolute inset-0 auth-grid-bg pointer-events-none opacity-60" />
        <p className="font-mono text-sm text-red-400 mb-4 max-w-sm">{statusError}</p>
        <button
          onClick={() => { setLoading(true); setStatusError(''); fetchDashboardData(); }}
          className="lumiere-primary-button relative rounded-xl px-5 py-3 text-sm font-bold transition-colors"
        >
          Tekrar Dene
        </button>
        <button
          onClick={handleLogout}
          className="relative mt-3 text-xs font-mono text-neutral-500 hover:text-neutral-300 underline"
        >
          Çıkış yap ve tekrar giriş yap
        </button>
      </div>
    );
  }

  // ==========================================
  // KİLİTLİ EKRAN (VERİ YOKSA)
  // ==========================================
  // Program Oluşturucu açıkken her zaman onu göster (dashboard'a geçişi onFinish yönetir)
  if (showProgramBuilder) {
    return (
      <ProgramBuilder
        mediaContext={programContext}
        onFinish={async () => {
          await fetchDashboardData();
          setShowProgramBuilder(false);
        }}
      />
    );
  }

  if (!isSetupComplete) {
    return (
      <OnboardingWizard
        onComplete={(context) => {
          setProgramContext(context || null);
          setShowProgramBuilder(true);
        }}
        setCurrentPage={setCurrentPage}
      />
    );
  }

  // ==========================================
  // CANLI DASHBOARD
  // ==========================================
  return (
    <div className="lumiere-app-shell app-dashboard text-neutral-100 font-sans antialiased">
      {activeTab !== 'flow' && (
        <header
          className="sticky top-0 z-50 border-b border-white/[0.07] bg-[#111118]/85 backdrop-blur-2xl"
          style={{ paddingTop: 'env(safe-area-inset-top)' }}
        >
          <div className="lp-column px-4">
            <div className="lp-phone-header">
              <div className="lp-brand">
                <div className="lp-brand-mark">
                  <Square strokeWidth={2.5} style={{ width: 'calc(18px * var(--lp-scale))', height: 'calc(18px * var(--lp-scale))' }} />
                </div>
                <div className="min-w-0">
                  <div className="lp-brand-name">
                    LUMIERE <b>COACHING</b>
                  </div>
                  {memberSince && (
                    <div className="lp-member-since truncate">{formatMemberSince(memberSince)}</div>
                  )}
                </div>
              </div>

              <div className="lp-header-actions">
                {isAdmin && (
                  <button
                    onClick={() => setAdminOpen(true)}
                    className="lp-icon-button"
                    aria-label="Admin paneli"
                  >
                    <Activity strokeWidth={2} />
                  </button>
                )}
                <button
                  onClick={() => setSettingsOpen(true)}
                  className="lp-icon-button"
                  aria-label="Ayarlar"
                >
                  <Settings strokeWidth={2} />
                </button>
                <button
                  onClick={handleLogout}
                  className="lp-icon-button"
                  aria-label="Çıkış yap"
                >
                  <LogOut strokeWidth={2} />
                </button>
              </div>
            </div>
          </div>
        </header>
      )}

      {/* Native app tarzı alt sekme çubuğu - mockup ölçülerinde, tüm ekran boyutlarında */}
      <nav className="lp-bottom-nav" aria-label="Sekmeler">
        {NAV_ITEMS.map(({ key, label }) => {
          const isActive = activeTab === key;
          return (
            <button
              key={key}
              onClick={() => navigateToTab(key)}
              className={isActive ? 'active' : ''}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="lp-nav-icon">
                {key === 'flow' && (
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <circle cx="12" cy="12" r="9" />
                    <circle cx="12" cy="12" r="5" />
                    <circle cx="12" cy="12" r="1.5" fill="currentColor" />
                  </svg>
                )}
                {key === 'chat' && (
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2">
                    <circle cx="12" cy="12" r="6" />
                  </svg>
                )}
                {key === 'daily' && (
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2">
                    <rect x="4" y="4" width="16" height="16" rx="3" />
                  </svg>
                )}
                {key === 'workout' && (
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                )}
                {key === 'nutrition' && (
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                  </svg>
                )}
                {key === 'progress' && (
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="7" y1="17" x2="17" y2="7" />
                    <polyline points="7 7 17 7 17 17" />
                  </svg>
                )}
              </span>
              {label}
            </button>
          );
        })}
      </nav>

      <SettingsMenu
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onLogout={handleLogout}
        permissions={permissions}
        onPermissionsChanged={fetchDashboardData}
      />
      <AdminPanel open={adminOpen} onClose={() => setAdminOpen(false)} />

      <main
        className="lp-main tab-swipe-surface lp-column px-4 mt-4 space-y-4 relative"
        onTouchStart={handleTabTouchStart}
        onTouchEnd={handleTabTouchEnd}
      >
        <div key={activeTab} className={`page-transition page-transition-${tabDirection > 0 ? 'next' : 'prev'}`}>

        {activeTab === 'flow' && (
          <FlowScreen
            profile={profile}
            workout={workout}
            nutritionPlans={nutritionPlans}
            onQuickAction={handleQuickAction}
            onNavigateTab={navigateToTab}
            onSetChatMessage={setChatInput}
            onOpenSettings={() => setSettingsOpen(true)}
            onLogout={handleLogout}
            memberSinceLabel={formatMemberSince(memberSince)}
          />
        )}

        {activeTab === 'chat' && (
          <JarvisChatPanel
            messages={chatMessages}
            input={chatInput}
            sending={chatSending}
            onInputChange={setChatInput}
            onSubmit={sendChatMessage}
            chatEndRef={chatEndRef}
          />
        )}

        {activeTab === 'daily' && (
          <div className="space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="lp-section-kicker">Günlük ritim</p>
                <h2 className="lp-screen-title">Bugünün <span>kaydı.</span></h2>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => shiftSelectedDate(-1)}
                  className="lp-icon-button" aria-label="Önceki gün">‹</button>
                <input
                  type="date" value={selectedDate} max={new Date().toISOString().split('T')[0]}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="bg-[#121219] border border-white/10 rounded-xl px-2 py-1.5 text-xs text-neutral-200 focus:outline-none focus:border-red-500"
                />
                <button onClick={() => shiftSelectedDate(1)} disabled={selectedDate >= new Date().toISOString().split('T')[0]}
                  className="lp-icon-button disabled:opacity-30" aria-label="Sonraki gün">›</button>
              </div>
            </div>

            {loadingDaily ? (
              <p className="lp-small lp-muted">Yükleniyor...</p>
            ) : (
              <div className="space-y-3">
                {dailyNutrition && (
                  <div className="lp-panel">
                    <div className="lp-panel-heading">
                      <strong>{formatDailyDate(selectedDate)}</strong>
                      <span>{selectedDate === new Date().toISOString().split('T')[0] ? 'Bugün' : 'Arşiv'}</span>
                    </div>
                    <div className="lp-stats">
                      <div className="lp-stat">
                        <div className="lp-ring red">{Math.round(dailyNutrition.summary.calories)}</div>
                        <label>Kalori</label>
                        <div className="lp-small lp-muted">/ {profile?.daily_calorie_target || 2200} kcal</div>
                      </div>
                      <div className="lp-stat">
                        <div className="lp-ring green">{Math.round(dailyNutrition.summary.protein)}g</div>
                        <label>Protein</label>
                        <div className="lp-small lp-muted">/ {profile?.daily_protein_target || 140}g</div>
                      </div>
                      <div className="lp-stat">
                        <div className="lp-ring">{dailyWorkout?.total_sets || 0}</div>
                        <label>Set</label>
                        <div className="lp-small lp-muted">antrenman</div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="lp-panel">
                  <div className="lp-panel-heading"><strong>Bugün yenenler</strong><span>{dailyNutrition?.meals?.length || 0} kayıt</span></div>
                  {dailyNutrition && dailyNutrition.meals && dailyNutrition.meals.length > 0 ? (
                    <div>
                      {dailyNutrition.meals.map((m) => (
                        <div key={m.id} className="lp-list-row">
                          <div className="lp-list-icon">☼</div>
                          <div>
                            <strong>{m.meal_name}</strong>
                            <small className="line-clamp-1 block">{m.ingredients}</small>
                          </div>
                          <span className="lp-chev lp-small lp-muted">{m.calories.toFixed(0)} kcal · {m.protein.toFixed(0)}g P</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="lp-small lp-muted">Bu gün için beslenme kaydı yok.</p>
                  )}
                </div>

                <div className="lp-panel">
                  <div className="lp-panel-heading"><strong>O gün yapılan antrenman</strong><span>{dailyWorkout?.total_sets || 0} set</span></div>
                  {dailyWorkout && dailyWorkout.logs && dailyWorkout.logs.length > 0 ? (
                    <div>
                      {dailyWorkout.logs.map((l, i) => (
                        <div key={i} className="lp-list-row">
                          <div className="lp-list-icon">{i + 1}</div>
                          <div>
                            <strong>{l.exercise_name}</strong>
                            <small>Set {l.set_number}</small>
                          </div>
                          <span className="lp-chev lp-small" style={{ color: 'var(--lp-red-2)' }}>{l.weight_lifted}kg × {l.reps_done}{l.rpe ? ` · RPE ${l.rpe}` : ''}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="lp-small lp-muted">Bu gün için antrenman kaydı yok.</p>
                  )}
                </div>

                {!loadingDaily && Object.keys(dailyHeatmap).length > 0 && (
                  <div className="lp-panel">
                    <div className="lp-panel-heading"><strong>Kas ısı haritası</strong><span>🔥</span></div>
                    <MuscleHeatmap data={dailyHeatmap} />
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'workout' && (
          <div className="space-y-3 animate-fadeIn">
            <div>
              <p className="lp-section-kicker">Bugünkü seans</p>
              <h2 className="lp-screen-title">Gücünü <span>inşa et.</span></h2>
            </div>

            {deloadStatus && deloadStatus.needs_deload && (
              <div className="lp-panel" style={{ borderColor: 'rgba(239,51,64,.35)', background: 'rgba(239,51,64,.08)' }}>
                <p className="text-sm font-bold" style={{ color: 'var(--lp-red-2)' }}>⚠️ Deload Haftası Önerisi</p>
                <p className="lp-small lp-muted mt-1">
                  Son antrenmanlarda durağanlık veya yüksek yorgunluk tespit edildi. Bu hafta
                  ağırlıkları %40-50 azaltıp toparlanmayı önceliklendirmeyi düşün.
                </p>
              </div>
            )}

            {(!workout.programs || workout.programs.length === 0) ? (
              <div className="lp-panel text-center space-y-3" style={{ borderStyle: 'dashed' }}>
                <p className="lp-small lp-muted">🏃‍♂️ Henüz aktif bir program yok.</p>
                <p className="lp-small lp-muted">AI üretimi 1-2 dakika sürebilir — butona bastıktan sonra beklemede kal.</p>
                {workoutError && (
                  <p className="lp-small px-3 py-2 rounded-xl" style={{ color: 'var(--lp-red-2)', background: 'rgba(239,51,64,.1)', border: '1px solid rgba(239,51,64,.3)' }}>
                    {workoutError}
                  </p>
                )}
                <button onClick={generateWorkoutProgram} disabled={generatingProgram} className="lp-primary">
                  {generatingProgram ? 'OLUŞTURULUYOR (1-2 DK SÜREBİLİR)...' : 'PROFİLİME GÖRE PROGRAM OLUŞTUR'}
                </button>
              </div>
            ) : (
              (() => {
              const dayNames = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi'];
              const todayName = dayNames[new Date().getDay()];
              const activeProg = workout.programs?.find((p) =>
                p.day_name?.toLocaleLowerCase('tr-TR').includes(todayName.toLocaleLowerCase('tr-TR'))
              ) || workout.programs?.[0];
              const exCount = activeProg?.exercises?.length || 0;
              const doneCount = workout.today_logs?.length || 0;
              const focusName = activeProg?.focus ? activeProg.focus.replace(/_/g, ' ') : 'Heavy focus';

              return activeProg ? (
                <>
                  <div className="lp-hero" style={{ marginTop: 'calc(16px * var(--lp-scale))' }}>
                    <div className="lp-section-kicker" style={{ color: '#ffd2d5' }}>
                      {activeProg.day_name} · {focusName}
                    </div>
                    <h2>
                      {activeProg.focus
                        ? activeProg.focus.replace(/_/g, ', ')
                        : 'Göğüs, omuz, triceps'}
                    </h2>
                    <p>{exCount} egzersiz · tahmini {Math.max(exCount * 7, 20)} dakika</p>
                    <div style={{ display: 'flex', gap: 'calc(7px * var(--lp-scale))' }}>
                      <button
                        type="button"
                        className="lp-primary"
                        style={{ background: '#fff', color: '#a71f2d', fontWeight: 900 }}
                      >
                        Seansa başla ›
                      </button>
                    </div>
                  </div>

                  <div className="lp-panel">
                    <div className="lp-panel-heading">
                      <strong>Egzersizler</strong>
                      <span className="lp-muted font-mono">{doneCount} / {exCount} tamamlandı</span>
                    </div>
                    <div>
                      {activeProg.exercises.map((ex, idx) => (
                        <div key={ex.id} className="lp-list-row">
                          <div className="lp-list-icon">{idx + 1}</div>
                          <div>
                            <strong>{ex.name}</strong>
                            <small>
                              {ex.target_sets} × {ex.target_reps}{ex.target_rpe ? ` · RIR ${Math.max(0, 10 - ex.target_rpe)}` : ' · RIR 2'}
                              {ex.equipment ? ` · ${ex.equipment}` : ''}
                            </small>
                            {ex.technique_cue && (
                              <small className="block" style={{ color: 'var(--lp-red-2)' }}>💡 {ex.technique_cue}</small>
                            )}
                          </div>
                          <span className="lp-chev">›</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : null;
            })())}

            <div className="lp-panel">
              <div className="lp-panel-heading"><strong>Bugün kaydedilen setler</strong><span>{workout.today_logs?.length || 0} set</span></div>
              {(!workout.today_logs || workout.today_logs.length === 0) ? (
                <p className="lp-small lp-muted">Bugün henüz set girilmedi.</p>
              ) : (
                <div>
                  {workout.today_logs.map((log, i) => (
                    <div key={i} className="lp-list-row">
                      <div className="lp-list-icon">{i + 1}</div>
                      <div>
                        <strong>{log.exercise_name}</strong>
                        <small>Set {log.set_number}</small>
                      </div>
                      <span className="lp-chev lp-small" style={{ color: 'var(--lp-green)' }}>{log.weight_lifted}kg × {log.reps_done}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'nutrition' && (
          <div className="space-y-3 animate-fadeIn">
            <div>
              <p className="lp-section-kicker">Beslenme laboratuvarı</p>
              <h2 className="lp-screen-title">Yakıtını <span>akıllı seç.</span></h2>
            </div>

            <FoodPhotoUpload
              preview={foodPhotoPreview}
              analyzing={foodPhotoAnalyzing}
              error={foodPhotoError}
              inputRef={foodPhotoInputRef}
              onFileSelect={analyzeFoodPhoto}
              onConfirm={confirmFoodPhoto}
              onCancel={() => { setFoodPhotoPreview(null); setFoodPhotoError(''); }}
            />

            <div className="lp-panel">
              <div className="lp-panel-heading">
                <strong>Lumiere'in önerdiği plan</strong>
                <span>{mealPlan.length > 0 ? `${mealPlan.length} öğün` : 'Henüz yok'}</span>
              </div>
              <div className="flex gap-2 mb-3">
                {mealPlan.length > 0 && (
                  <button onClick={deleteMealPlan}
                    className="lp-ghost" style={{ color: '#ff858c', borderColor: 'rgba(239,51,64,.24)' }}>
                    KALDIR
                  </button>
                )}
                <button onClick={regenerateMealPlan} disabled={generatingPlan} className="lp-primary">
                  {generatingPlan ? 'OLUŞTURULUYOR...' : 'YENİ PLAN OLUŞTUR'}
                </button>
              </div>
              {mealPlan.length === 0 ? (
                <p className="lp-small lp-muted">Henüz bir plan yok. Telegram'da /beslenme yaz veya yukarıdaki butona bas.</p>
              ) : (
                <div>
                  {mealPlan.map((item) => (
                    <div key={item.id} className="lp-plan-card">
                      <div className="flex justify-between gap-2 items-baseline">
                        <strong className="text-sm">{item.meal_name}</strong>
                        <small className="lp-muted">{item.time_target}</small>
                      </div>
                      <p className="lp-small lp-muted">{item.description}</p>
                      <span className="lp-small block mt-1" style={{ color: 'var(--lp-green)' }}>
                        {item.calories.toFixed(0)} kcal · P:{item.protein.toFixed(0)}g · K:{item.carbs.toFixed(0)}g · Y:{item.fats.toFixed(0)}g
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="lp-panel">
              <div className="lp-panel-heading"><strong>Bugünkü ilerleme</strong><span>halka</span></div>
              <div className="relative flex items-center justify-center my-2">
                <svg className="w-32 h-32 transform -rotate-90">
                  <circle cx="80" cy="80" r="50" className="text-neutral-800" strokeWidth="10" fill="transparent" />
                  <circle cx="80" cy="80" r="50" className="text-emerald-500 transition-all duration-500" strokeWidth="10" strokeDasharray={2 * Math.PI * 50} strokeDashoffset={dashOffset} strokeLinecap="round" fill="transparent" />
                </svg>
                <div className="absolute text-center">
                  <span className="text-2xl font-black block">{consumedCalories.toFixed(0)}</span>
                  <span className="lp-small lp-muted uppercase">/ {targetCalories.toFixed(0)} kcal</span>
                </div>
              </div>
              <div className="space-y-3 mt-4">
                <MacroBar label="PROTEİN" value={consumedProtein} target={targetProtein} color="bg-emerald-500" />
                <MacroBar label="KARBONHİDRAT" value={consumedCarbs} target={targetCarbs} color="bg-red-500" />
              </div>
            </div>

            <div className="lp-panel">
              <div className="lp-panel-heading"><strong>Bugün gerçekten yediklerin</strong><span>{nutritionPlans.length} kayıt</span></div>
              {nutritionPlans.length === 0 ? (
                <p className="lp-small lp-muted">Bugün henüz öğün girilmedi.</p>
              ) : (
                <div>
                  {nutritionPlans.map((plan) => (
                    <div key={plan.id} className="lp-list-row">
                      <div className="lp-list-icon">▣</div>
                      <div>
                        <strong>{plan.meal_name} {plan.time_target ? `(${plan.time_target})` : ''}</strong>
                        <small className="line-clamp-1 block">{plan.ingredients}</small>
                      </div>
                      <span className="lp-chev lp-small" style={{ color: 'var(--lp-green)' }}>
                        {plan.calories.toFixed(0)} kcal · P:{plan.target_protein}g
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'progress' && (
          <div className="space-y-3 animate-fadeIn">
            <div>
              <p className="lp-section-kicker">Veriye bak</p>
              <h2 className="lp-screen-title">İlerlemeni <span>gör.</span></h2>
            </div>

            {/* 1. Kilo trendi ana panel - media_1788809344896.png birebir */}
            <div className="lp-panel" style={{ marginTop: 'calc(16px * var(--lp-scale))' }}>
              <div className="lp-panel-heading">
                <strong>Kilo trendi</strong>
                <span style={{ color: 'var(--lp-red-2)' }}>Son 8 hafta</span>
              </div>
              <div className="lp-chart">
                <svg viewBox="0 0 360 135" preserveAspectRatio="none" style={{ width: '100%', height: '100%' }}>
                  <defs>
                    <linearGradient id="progressWaveFill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0" stopColor="#ef3340" stopOpacity="0.38" />
                      <stop offset="1" stopColor="#ef3340" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path d="M0 97 C35 90 50 101 78 87 S125 80 150 87 S192 70 220 76 S264 62 292 66 S332 50 360 42 V135 H0Z" fill="url(#progressWaveFill)" />
                  <path d="M0 97 C35 90 50 101 78 87 S125 80 150 87 S192 70 220 76 S264 62 292 66 S332 50 360 42" fill="none" stroke="#ff6871" strokeWidth="3" />
                </svg>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 'calc(12px * var(--lp-scale))' }}>
                <div>
                  <strong style={{ fontSize: 'calc(24px * var(--lp-scale))', fontWeight: 900, letterSpacing: '-0.05em' }}>
                    {latestWeight ? `${Number(latestWeight).toFixed(1)} kg` : '72.4 kg'}
                  </strong>
                  <div className="lp-small lp-muted" style={{ marginTop: '2px' }}>
                    {weightDelta !== null
                      ? `${weightDelta > 0 ? '+' : ''}${weightDelta.toFixed(1)} kg · hedefe doğru`
                      : '−1.8 kg · hedefe doğru'}
                  </div>
                </div>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#888894', fontSize: 'calc(10px * var(--lp-scale))' }}>
                  <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--lp-green)' }} />
                  hedef çizgisi
                </div>
              </div>
            </div>

            {/* 2. Üçlü istatistik grubu */}
            <div className="lp-stats" style={{ marginTop: 'calc(12px * var(--lp-scale))' }}>
              <div className="lp-stat" style={{ padding: 'calc(14px * var(--lp-scale)) 4px' }}>
                <strong style={{ display: 'block', fontSize: 'calc(19px * var(--lp-scale))', fontWeight: 900 }}>
                  {metrics.length > 0 ? metrics.length : 8}
                </strong>
                <div className="lp-small lp-muted">kilo kaydı</div>
              </div>
              <div className="lp-stat" style={{ padding: 'calc(14px * var(--lp-scale)) 4px' }}>
                <strong style={{ display: 'block', fontSize: 'calc(19px * var(--lp-scale))', fontWeight: 900 }}>
                  {workout.today_logs?.length || 12}
                </strong>
                <div className="lp-small lp-muted">antrenman</div>
              </div>
              <div className="lp-stat" style={{ padding: 'calc(14px * var(--lp-scale)) 4px' }}>
                <strong style={{ display: 'block', fontSize: 'calc(19px * var(--lp-scale))', fontWeight: 900 }}>86%</strong>
                <div className="lp-small lp-muted">istikrar</div>
              </div>
            </div>

            {/* 3. Son içgörü kartı */}
            <div className="lp-panel">
              <div className="lp-panel-heading">
                <strong>Son içgörü</strong>
                <span style={{ color: 'var(--lp-red-2)' }}>Lumiere</span>
              </div>
              <p className="lp-small lp-muted" style={{ margin: 0, lineHeight: 1.5 }}>
                {insights[0]?.content || 'Son iki haftada antrenman devamlılığın yükseldi; aynı ritmi koru.'}
              </p>
            </div>

            {/* Detaylı grafikler & analiz aracı (isteğe bağlı genişletme) */}
            <ProgressChartsSection
              chartData={chartData}
              loading={loadingCharts}
              weightDelta={weightDelta}
              weightInput={weightInput}
              savingWeight={savingWeight}
              onWeightInputChange={setWeightInput}
              onSubmitWeight={submitWeight}
            />

            <div className="lp-panel">
              <div className="lp-panel-heading"><strong>Lumiere'in analizleri</strong><span>✦</span></div>
              <button onClick={runWeeklyAnalysis} disabled={analyzing} className="lp-primary mb-3">
                {analyzing ? 'ANALİZ EDİLİYOR...' : 'ŞİMDİ ANALİZ ET'}
              </button>
              {insights.length === 0 ? (
                <p className="lp-small lp-muted">Henüz kayıtlı içgörü yok. Bir hafta veri girdikten sonra "Şimdi Analiz Et" butonuna bas.</p>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar pr-1">
                  {insights.map((ins) => (
                    <div key={ins.id} className="lp-list-row">
                      <div className="lp-list-icon">✦</div>
                      <div>
                        <strong style={{ color: 'var(--lp-red-2)' }}>{ins.category}</strong>
                        <small className="whitespace-pre-line">{ins.content}</small>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        </div>

      </main>
    </div>
  );
}

function MacroBar({ label, value, target, color }) {
  const pct = Math.min((value / target) * 100, 100);
  return (
    <div>
      <div className="flex justify-between mb-1.5 text-sm">
        <span className="text-neutral-400">{label}</span>
        <span className="font-bold font-mono text-neutral-200">{value.toFixed(0)}g / {target.toFixed(0)}g</span>
      </div>
      <div className="w-full bg-neutral-950 h-2 rounded-full overflow-hidden border border-neutral-800/50">
        <div className={`${color} h-full rounded-full transition-all duration-500`} style={{ width: `${pct}%` }}></div>
      </div>
    </div>
  );
}

const CHART_TOOLTIP_STYLE = {
  contentStyle: { background: '#171717', border: '1px solid #404040', borderRadius: '8px', fontSize: '11px' },
  labelStyle: { color: '#a3a3a3' },
};

function JarvisChatPanel({
  messages, input, sending,
  onInputChange, onSubmit, chatEndRef,
}) {
  const hints = [
    '3 yumurta yedim',
    'bench 80kg x 8',
    'bugün çok yorgunum',
    'neden bu programı seçtin?',
    'bu hafta vs geçen hafta',
    'bugün ne önerirsin?',
  ];

  return (
    <div
      className="lp-panel animate-fadeIn flex flex-col overflow-hidden"
      style={{ height: 'calc(100dvh - 14rem)', minHeight: '26rem', padding: 0 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.08] bg-black/10 shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="lp-brand-mark shrink-0" style={{ width: 'calc(34px * var(--lp-scale))', height: 'calc(34px * var(--lp-scale))' }}>
            <Cpu strokeWidth={2.25} />
          </div>
          <div className="min-w-0">
            <p className="lp-section-kicker">Kişisel AI koçun</p>
            <h2 className="lp-brand-name mt-0.5">Lumiere <b>yanında.</b></h2>
          </div>
        </div>
        <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold text-emerald-300 shrink-0">
          <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
          <span>Hazır</span>
        </div>
      </div>

      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 scrollbar-hide">
        {messages.length === 0 && !sending && (
          <div className="h-full flex flex-col items-center justify-center text-center gap-3 opacity-40">
            <Cpu className="w-12 h-12 text-red-500" strokeWidth={1} />
            <p className="lp-small lp-muted">Bugün neye odaklanalım? Antrenman, beslenme ya da gelişimin hakkında yaz.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slideUp`}>
            <div className={`lp-chat-bubble ${msg.role === 'user' ? 'user' : ''}`}>
              {msg.text}

              {msg.role === 'jarvis' && msg.intent && msg.intent !== 'chat' && (
                <span className="block mt-1.5 text-[9px] font-mono uppercase tracking-wide" style={{ color: 'var(--lp-red-2)' }}>
                  {msg.intent.replace(/_/g, ' ')}
                </span>
              )}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start animate-pulse">
            <div className="lp-chat-bubble flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce" />
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-3 bg-black/10 border-t border-white/[0.08] shrink-0">
        <form onSubmit={onSubmit} className="lp-jarvis-input">
          <input
            type="text"
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            placeholder="Mesajını yaz..."
            disabled={sending}
            className="flex-1 min-w-0 bg-transparent border-0 focus:outline-none text-[13px] text-neutral-100 placeholder:text-[#656571] disabled:opacity-50"
          />
          <button type="submit" disabled={sending || !input.trim()} className="lp-send" aria-label="Gönder">
            <Send className="w-3.5 h-3.5" strokeWidth={2.5} />
          </button>
        </form>

        <div className="flex gap-2 mt-2.5 overflow-x-auto pb-1 scrollbar-hide">
          {hints.map((hint) => (
            <button key={hint} type="button" onClick={() => onInputChange(hint)}
              className="lp-ghost whitespace-nowrap shrink-0">
              {hint}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function FoodPhotoUpload({ preview, analyzing, error, inputRef, onFileSelect, onConfirm, onCancel }) {
  return (
    <div className="lp-panel space-y-3">
      <div className="flex justify-between items-center">
        <h3 className="text-xs font-mono uppercase text-neutral-400 tracking-wider">📸 Tabak Fotoğrafı ile Kaydet</h3>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => { if (e.target.files?.[0]) onFileSelect(e.target.files[0]); e.target.value = ''; }}
        />
        {!preview && (
          <button
            onClick={() => inputRef.current?.click()}
            disabled={analyzing}
            className="bg-emerald-500 text-black text-xs font-bold px-4 py-2 rounded-lg disabled:opacity-50"
          >
            {analyzing ? 'ANALİZ EDİLİYOR...' : 'FOTOĞRAF YÜKLE'}
          </button>
        )}
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {preview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <img src={preview.previewUrl} alt="Yemek" className="rounded-xl border border-neutral-800 w-full max-h-48 object-cover" />
          <div className="space-y-3">
            <div>
              <p className="font-bold text-white">{preview.meal_name}</p>
              <p className="text-xs text-neutral-400 mt-1">{preview.description}</p>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <span className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2">{preview.calories?.toFixed(0)} kcal</span>
              <span className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2">{preview.protein?.toFixed(0)}g protein</span>
              <span className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2">{preview.carbs?.toFixed(0)}g karb</span>
              <span className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2">{preview.fats?.toFixed(0)}g yağ</span>
            </div>
            {preview.confidence === 'low' && (
              <p className="text-[10px] text-red-400 font-mono">⚠️ Düşük güven — makroları kontrol edin</p>
            )}
            <div className="flex gap-2">
              <button onClick={onCancel} className="flex-1 bg-neutral-800 text-white text-xs font-bold py-2.5 rounded-lg">İPTAL</button>
              <button onClick={onConfirm} className="flex-1 bg-emerald-500 text-black text-xs font-bold py-2.5 rounded-lg">KAYDET</button>
            </div>
          </div>
        </div>
      )}

      {!preview && !analyzing && (
        <p className="text-xs text-neutral-600 font-mono">Tabak fotoğrafını yükle — AI makroları hesaplasın, sen onayla.</p>
      )}
    </div>
  );
}

function ProgressChartsSection({ chartData, loading, weightDelta, weightInput, savingWeight, onWeightInputChange, onSubmitWeight }) {
  const formatDate = (d) => {
    if (!d) return '';
    const parts = d.split('-');
    return parts.length >= 3 ? `${parts[2]}/${parts[1]}` : d;
  };

  const nutritionChart = chartData?.nutrition?.map((d) => ({
    ...d,
    label: formatDate(d.date),
    calTarget: chartData?.targets?.calories || 0,
    protTarget: chartData?.targets?.protein || 0,
  })) || [];

  const weightChart = chartData?.weight?.map((d) => ({
    ...d,
    label: formatDate(d.date),
  })) || [];

  const volumeChart = chartData?.volume || [];

  if (loading) {
    return <p className="text-sm text-neutral-600 font-mono">Grafikler yükleniyor...</p>;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Kilo trendi */}
      <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl space-y-4">
        <h3 className="text-xs font-mono uppercase text-neutral-400 tracking-wider">Kilo Trendi (14 gün)</h3>
        {weightChart.length === 0 ? (
          <p className="text-sm text-neutral-600 font-mono">Henüz kilo kaydı yok.</p>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={weightChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="label" tick={{ fill: '#737373', fontSize: 10 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: '#737373', fontSize: 10 }} width={35} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE.contentStyle} formatter={(v) => [`${v} kg`, 'Kilo']} />
              <Line type="monotone" dataKey="weight" stroke="#ef3340" strokeWidth={2} dot={{ fill: '#ef3340', r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
        {weightDelta !== null && (
          <p className="text-xs font-mono text-neutral-400">
            Dönem değişimi: <span className={weightDelta <= 0 ? 'text-emerald-400' : 'text-red-400'}>{weightDelta > 0 ? '+' : ''}{weightDelta.toFixed(1)} kg</span>
          </p>
        )}
        <form onSubmit={onSubmitWeight} className="flex gap-2 pt-2">
          <input type="number" step="0.1" placeholder="kg" value={weightInput}
            onChange={(e) => onWeightInputChange(e.target.value)}
            className="flex-1 bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-red-500" />
          <button type="submit" disabled={savingWeight}
            className="bg-red-500 text-white text-xs font-bold px-4 py-2 rounded-lg disabled:opacity-50">
            {savingWeight ? '...' : 'KAYDET'}
          </button>
        </form>
      </div>

      {/* Makro uyumu */}
      <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl space-y-4">
        <h3 className="text-xs font-mono uppercase text-neutral-400 tracking-wider">Günlük Kalori (Plan vs Gerçek)</h3>
        {nutritionChart.length === 0 ? (
          <p className="text-sm text-neutral-600 font-mono">Beslenme verisi yok.</p>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={nutritionChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="label" tick={{ fill: '#737373', fontSize: 10 }} />
              <YAxis tick={{ fill: '#737373', fontSize: 10 }} width={40} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE.contentStyle} />
              <ReferenceLine y={chartData?.targets?.calories} stroke="#10b981" strokeDasharray="4 4" label={{ value: 'Hedef', fill: '#10b981', fontSize: 10 }} />
              <Bar dataKey="calories" fill="#ef3340" radius={[4, 4, 0, 0]} name="Kalori" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Protein trendi */}
      <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl space-y-4">
        <h3 className="text-xs font-mono uppercase text-neutral-400 tracking-wider">Günlük Protein</h3>
        {nutritionChart.length === 0 ? (
          <p className="text-sm text-neutral-600 font-mono">Protein verisi yok.</p>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={nutritionChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="label" tick={{ fill: '#737373', fontSize: 10 }} />
              <YAxis tick={{ fill: '#737373', fontSize: 10 }} width={40} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE.contentStyle} formatter={(v) => [`${v}g`, 'Protein']} />
              <ReferenceLine y={chartData?.targets?.protein} stroke="#10b981" strokeDasharray="4 4" />
              <Bar dataKey="protein" fill="#10b981" radius={[4, 4, 0, 0]} name="Protein (g)" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Kas hacmi */}
      <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-2xl space-y-4">
        <h3 className="text-xs font-mono uppercase text-neutral-400 tracking-wider">Haftalık Kas Grubu Hacmi (Set)</h3>
        {volumeChart.length === 0 ? (
          <p className="text-sm text-neutral-600 font-mono">Antrenman verisi yok.</p>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={volumeChart} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#737373', fontSize: 10 }} />
              <YAxis type="category" dataKey="muscle_group" tick={{ fill: '#a3a3a3', fontSize: 10 }} width={60} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE.contentStyle} formatter={(v) => [`${v} set`, 'Hacim']} />
              <Bar dataKey="sets" fill="#c92231" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

// Set sayısına göre ısı rengi belirler. Eşikler haftalık hipertrofi hacim standartlarına
// yaklaşık dayanır (haftada ~10-20 set/kas grubu optimal aralık kabul edilir).
function getHeatColor(sets) {
  if (!sets || sets === 0) return '#3f3f46';        // neutral-700 - hiç çalışılmamış (nötr gri gövde)
  if (sets <= 4) return '#a16207';                   // amber-700 - düşük
  if (sets <= 8) return '#ef3340';                   // red-500 - orta
  if (sets <= 14) return '#c92231';                  // red-600 - yüksek
  return '#dc2626';                                  // red-600 - çok yüksek
}

// getHeatColor ile aynı eşiklere göre, o yoğunluk kovasının <defs> içinde tanımlı
// gradyanına referans döner - düz renk yerine "dolgun/parlak kas" hissi veren
// hafif 3D degradeler için kullanılır.
function getHeatGradientId(sets) {
  if (!sets || sets === 0) return 'heatNone';
  if (sets <= 4) return 'heatLow';
  if (sets <= 8) return 'heatMed';
  if (sets <= 14) return 'heatHigh';
  return 'heatMax';
}

// Referans anatomi görseline benzer, profesyonel/anatomik ÖN ve ARKA gövdeyi yan yana
// gösteren ısı haritası. Nötr, gölgeli-gri bir vücut siluetinin üzerine, o gün çalışılan
// kas gruplarını degrade renkle ve hafif "glow" ile vurguluyor - çalışılmayan kaslar
// gri anatomik detayında kalırken, çalışılanlar referans fotoğraftaki gibi öne çıkıyor.
// Kol ve Bacak hem ön (biceps/quad) hem arka (triceps/hamstring-glute) görünümde aynı
// renkte çıkar çünkü veri modelimizde bu ayrım yok, tek "Kol"/"Bacak" kategorisi var.
function MuscleHeatmap({ data }) {
  const sets = (group) => (data[group]?.sets) || 0;
  const fillFor = (group) => `url(#${getHeatGradientId(sets(group))})`;
  const glowFor = (group) => (sets(group) > 0 ? 'url(#muscleGlow)' : undefined);
  const neutral = 'url(#neutralGrad)'; // el, ayak, kafa gibi takip edilmeyen bölgeler
  const seam = 'rgba(0,0,0,0.35)'; // kas ayrım/tanım çizgileri

  const legendGroups = ['Göğüs', 'Sırt', 'Omuz', 'Kol', 'Karın', 'Bacak'];

  return (
    <div className="flex flex-col md:flex-row items-center gap-6">
      <svg viewBox="0 0 480 400" className="w-full max-w-lg h-auto shrink-0">
        <defs>
          <radialGradient id="neutralGrad" cx="35%" cy="30%" r="75%">
            <stop offset="0%" stopColor="#52525b" />
            <stop offset="100%" stopColor="#26262a" />
          </radialGradient>
          <radialGradient id="heatNone" cx="35%" cy="30%" r="75%">
            <stop offset="0%" stopColor="#52525b" />
            <stop offset="100%" stopColor="#303035" />
          </radialGradient>
          <radialGradient id="heatLow" cx="35%" cy="30%" r="75%">
            <stop offset="0%" stopColor="#d97706" />
            <stop offset="100%" stopColor="#78350f" />
          </radialGradient>
          <radialGradient id="heatMed" cx="35%" cy="30%" r="75%">
            <stop offset="0%" stopColor="#fdba74" />
            <stop offset="100%" stopColor="#c92231" />
          </radialGradient>
          <radialGradient id="heatHigh" cx="35%" cy="30%" r="75%">
            <stop offset="0%" stopColor="#fb923c" />
            <stop offset="100%" stopColor="#c2410c" />
          </radialGradient>
          <radialGradient id="heatMax" cx="35%" cy="30%" r="75%">
            <stop offset="0%" stopColor="#f87171" />
            <stop offset="100%" stopColor="#b91c1c" />
          </radialGradient>
          <filter id="muscleGlow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="3.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ========== ÖN GÖRÜNÜM ========== */}
        <g>
          <text x="95" y="14" textAnchor="middle" className="fill-neutral-500" style={{ font: '9px monospace', letterSpacing: '1px' }}>ÖN</text>
          {/* Kafa + boyun */}
          <ellipse cx="95" cy="34" rx="14" ry="17" fill={neutral} />
          <path d="M85,48 L105,48 L102,64 L88,64 Z" fill={neutral} />
          {/* Trapez (Sırt - önden az görünen kısım) */}
          <path d="M66,66 C78,58 95,54 95,54 C95,54 112,58 124,66 L113,76 C104,70 95,68 95,68 C95,68 86,70 77,76 Z" fill={fillFor('Sırt')} filter={glowFor('Sırt')} stroke={seam} strokeWidth="0.6" />
          {/* Omuzlar (anterior deltoid) */}
          <path d="M66,68 C50,68 40,80 40,96 C40,108 48,116 58,114 C66,112 70,98 70,86 C70,78 69,72 66,68 Z" fill={fillFor('Omuz')} filter={glowFor('Omuz')} stroke={seam} strokeWidth="0.6" />
          <path d="M124,68 C140,68 150,80 150,96 C150,108 142,116 132,114 C124,112 120,98 120,86 C120,78 121,72 124,68 Z" fill={fillFor('Omuz')} filter={glowFor('Omuz')} stroke={seam} strokeWidth="0.6" />
          <path d="M52,84 C55,90 56,98 55,106" fill="none" stroke={seam} strokeWidth="0.6" opacity="0.5" />
          <path d="M138,84 C135,90 134,98 135,106" fill="none" stroke={seam} strokeWidth="0.6" opacity="0.5" />
          {/* Göğüs (pektoral - üst/alt ayrımlı, ortada sternum çizgisi) */}
          <path d="M95,66 C82,62 68,66 63,80 C59,94 63,110 78,116 C88,120 94,114 95,104 Z" fill={fillFor('Göğüs')} filter={glowFor('Göğüs')} stroke={seam} strokeWidth="0.6" />
          <path d="M95,66 C108,62 122,66 127,80 C131,94 127,110 112,116 C102,120 96,114 95,104 Z" fill={fillFor('Göğüs')} filter={glowFor('Göğüs')} stroke={seam} strokeWidth="0.6" />
          <path d="M95,66 L95,116" fill="none" stroke={seam} strokeWidth="1" opacity="0.6" />
          <path d="M68,88 C76,92 84,94 93,94" fill="none" stroke={seam} strokeWidth="0.5" opacity="0.35" />
          <path d="M122,88 C114,92 106,94 97,94" fill="none" stroke={seam} strokeWidth="0.5" opacity="0.35" />
          {/* Serratus anterior - kaburga altı çizgiler (dekoratif, nötr) */}
          <path d="M64,102 L72,108 M62,110 L71,115 M120,110 L129,115 M118,102 L126,108" fill="none" stroke={seam} strokeWidth="0.5" opacity="0.3" />
          {/* Kollar (biceps) */}
          <path d="M48,92 C36,98 32,112 34,132 C35,146 39,158 46,160 C52,162 56,156 55,144 C54,130 52,116 52,104 C52,98 51,94 48,92 Z" fill={fillFor('Kol')} filter={glowFor('Kol')} stroke={seam} strokeWidth="0.6" />
          <path d="M142,92 C154,98 158,112 156,132 C155,146 151,158 144,160 C138,162 134,156 135,144 C136,130 138,116 138,104 C138,98 139,94 142,92 Z" fill={fillFor('Kol')} filter={glowFor('Kol')} stroke={seam} strokeWidth="0.6" />
          {/* Ön kollar */}
          <path d="M38,158 C36,172 37,188 42,200 C45,206 52,206 53,198 C55,184 54,170 51,158 Z" fill={fillFor('Kol')} filter={glowFor('Kol')} stroke={seam} strokeWidth="0.5" />
          <path d="M152,158 C154,172 153,188 148,200 C145,206 138,206 137,198 C135,184 136,170 139,158 Z" fill={fillFor('Kol')} filter={glowFor('Kol')} stroke={seam} strokeWidth="0.5" />
          {/* Karın (6 parçalı, üstten alta daralan) + obliques */}
          <path d="M62,96 C58,110 58,126 62,140 C66,152 74,158 80,158 L80,96 Z" fill={fillFor('Karın')} filter={glowFor('Karın')} stroke={seam} strokeWidth="0.5" opacity="0.9" />
          <path d="M128,96 C132,110 132,126 128,140 C124,152 116,158 110,158 L110,96 Z" fill={fillFor('Karın')} filter={glowFor('Karın')} stroke={seam} strokeWidth="0.5" opacity="0.9" />
          {[0, 1, 2].map((row) => (
            <g key={row}>
              <rect x={81} y={98 + row * 18} width={row === 2 ? 12 : 13} height={row === 2 ? 15 : 16} rx="3" fill={fillFor('Karın')} filter={glowFor('Karın')} stroke={seam} strokeWidth="0.5" />
              <rect x={96 - (row === 2 ? 1 : 0)} y={98 + row * 18} width={row === 2 ? 12 : 13} height={row === 2 ? 15 : 16} rx="3" fill={fillFor('Karın')} filter={glowFor('Karın')} stroke={seam} strokeWidth="0.5" />
            </g>
          ))}
          <path d="M95,96 L95,158" fill="none" stroke={seam} strokeWidth="0.8" opacity="0.5" />
          {/* Kalça/hip taper */}
          <path d="M65,158 C62,166 63,172 68,176 L122,176 C127,172 128,166 125,158 Z" fill={neutral} />
          {/* Bacaklar (quad - iç/dış ayrımlı) */}
          <path d="M80,178 C70,192 66,220 68,252 C69,270 74,282 82,283 C88,284 90,272 89,254 C88,234 90,214 88,196 C87,188 84,182 80,178 Z" fill={fillFor('Bacak')} filter={glowFor('Bacak')} stroke={seam} strokeWidth="0.6" />
          <path d="M110,178 C120,192 124,220 122,252 C121,270 116,282 108,283 C102,284 100,272 101,254 C102,234 100,214 102,196 C103,188 106,182 110,178 Z" fill={fillFor('Bacak')} filter={glowFor('Bacak')} stroke={seam} strokeWidth="0.6" />
          <path d="M85,190 C83,212 83,236 85,258" fill="none" stroke={seam} strokeWidth="0.5" opacity="0.4" />
          <path d="M105,190 C107,212 107,236 105,258" fill="none" stroke={seam} strokeWidth="0.5" opacity="0.4" />
          {/* Alt bacak (kalf - nötr) */}
          <path d="M71,286 C68,302 68,320 72,336 C74,344 82,344 84,336 C87,320 87,302 85,286 Z" fill={neutral} />
          <path d="M109,286 C112,302 112,320 108,336 C106,344 98,344 96,336 C93,320 93,302 95,286 Z" fill={neutral} />
          {/* Ayaklar */}
          <ellipse cx="77" cy="350" rx="9" ry="6" fill={neutral} />
          <ellipse cx="103" cy="350" rx="9" ry="6" fill={neutral} />
        </g>

        {/* ========== ARKA GÖRÜNÜM ========== */}
        <g transform="translate(260, 0)">
          <text x="95" y="14" textAnchor="middle" className="fill-neutral-500" style={{ font: '9px monospace', letterSpacing: '1px' }}>ARKA</text>
          <ellipse cx="95" cy="34" rx="14" ry="17" fill={neutral} />
          <path d="M85,48 L105,48 L102,64 L88,64 Z" fill={neutral} />
          {/* Trapez (büyük kite şekli, boyundan belin ortasına) */}
          <path d="M95,52 L124,66 L136,96 L95,116 L54,96 L66,66 Z" fill={fillFor('Sırt')} filter={glowFor('Sırt')} stroke={seam} strokeWidth="0.6" />
          {/* Arka omuz (posterior deltoid) */}
          <path d="M66,68 C50,68 40,80 40,96 C40,108 48,116 58,114 C66,112 70,98 70,86 C70,78 69,72 66,68 Z" fill={fillFor('Omuz')} filter={glowFor('Omuz')} stroke={seam} strokeWidth="0.6" />
          <path d="M124,68 C140,68 150,80 150,96 C150,108 142,116 132,114 C124,112 120,98 120,86 C120,78 121,72 124,68 Z" fill={fillFor('Omuz')} filter={glowFor('Omuz')} stroke={seam} strokeWidth="0.6" />
          {/* Lats (kanat şeklinde geniş sırt kası) */}
          <path d="M70,98 C56,106 50,128 58,152 C64,168 80,176 92,168 L92,116 Z" fill={fillFor('Sırt')} filter={glowFor('Sırt')} stroke={seam} strokeWidth="0.6" />
          <path d="M120,98 C134,106 140,128 132,152 C126,168 110,176 98,168 L98,116 Z" fill={fillFor('Sırt')} filter={glowFor('Sırt')} stroke={seam} strokeWidth="0.6" />
          {/* Erector spinae - omurga boyunca ince şeritler */}
          <path d="M91,112 C89,130 89,150 91,168" fill="none" stroke={seam} strokeWidth="1" opacity="0.5" />
          <path d="M99,112 C101,130 101,150 99,168" fill="none" stroke={seam} strokeWidth="1" opacity="0.5" />
          {/* Triceps */}
          <path d="M48,92 C36,98 32,112 34,132 C35,146 39,158 46,160 C52,162 56,156 55,144 C54,130 52,116 52,104 C52,98 51,94 48,92 Z" fill={fillFor('Kol')} filter={glowFor('Kol')} stroke={seam} strokeWidth="0.6" />
          <path d="M142,92 C154,98 158,112 156,132 C155,146 151,158 144,160 C138,162 134,156 135,144 C136,130 138,116 138,104 C138,98 139,94 142,92 Z" fill={fillFor('Kol')} filter={glowFor('Kol')} stroke={seam} strokeWidth="0.6" />
          <path d="M42,108 C46,118 47,130 45,142" fill="none" stroke={seam} strokeWidth="0.5" opacity="0.4" />
          <path d="M148,108 C144,118 143,130 145,142" fill="none" stroke={seam} strokeWidth="0.5" opacity="0.4" />
          {/* Ön kollar */}
          <path d="M38,158 C36,172 37,188 42,200 C45,206 52,206 53,198 C55,184 54,170 51,158 Z" fill={fillFor('Kol')} filter={glowFor('Kol')} stroke={seam} strokeWidth="0.5" />
          <path d="M152,158 C154,172 153,188 148,200 C145,206 138,206 137,198 C135,184 136,170 139,158 Z" fill={fillFor('Kol')} filter={glowFor('Kol')} stroke={seam} strokeWidth="0.5" />
          {/* Bel - alt sırt (lumbar) */}
          <path d="M83,168 L107,168 L103,182 L87,182 Z" fill={fillFor('Sırt')} filter={glowFor('Sırt')} stroke={seam} strokeWidth="0.5" />
          {/* Kalça (glute) - orta hat çizgili */}
          <path d="M67,182 C58,188 56,204 62,216 C68,226 88,228 93,216 C96,208 94,192 88,182 Z" fill={fillFor('Bacak')} filter={glowFor('Bacak')} stroke={seam} strokeWidth="0.6" />
          <path d="M123,182 C132,188 134,204 128,216 C122,226 102,228 97,216 C94,208 96,192 102,182 Z" fill={fillFor('Bacak')} filter={glowFor('Bacak')} stroke={seam} strokeWidth="0.6" />
          <path d="M95,182 L95,222" fill="none" stroke={seam} strokeWidth="0.7" opacity="0.45" />
          {/* Hamstring (bacak arkası - iç/dış ayrımlı) */}
          <path d="M65,222 C60,242 60,262 65,280 C68,290 76,290 78,280 C81,262 80,242 76,224 Z" fill={fillFor('Bacak')} filter={glowFor('Bacak')} stroke={seam} strokeWidth="0.5" />
          <path d="M125,222 C130,242 130,262 125,280 C122,290 114,290 112,280 C109,262 110,242 114,224 Z" fill={fillFor('Bacak')} filter={glowFor('Bacak')} stroke={seam} strokeWidth="0.5" />
          <path d="M87,224 C89,244 89,262 87,278" fill="none" stroke={seam} strokeWidth="0.5" opacity="0.35" />
          <path d="M103,224 C101,244 101,262 103,278" fill="none" stroke={seam} strokeWidth="0.5" opacity="0.35" />
          {/* Kalf (nötr, ikiye ayrık gastrocnemius görünümü) */}
          <path d="M67,286 C63,302 64,320 70,336 C73,343 82,343 83,335 C85,320 84,302 80,286 Z" fill={neutral} />
          <path d="M113,286 C117,302 116,320 110,336 C107,343 98,343 97,335 C95,320 96,302 100,286 Z" fill={neutral} />
          <ellipse cx="77" cy="350" rx="9" ry="6" fill={neutral} />
          <ellipse cx="103" cy="350" rx="9" ry="6" fill={neutral} />
        </g>
      </svg>

      <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs font-mono w-full md:w-52 shrink-0">
        {legendGroups.map((group) => (
          <div key={group} className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm shrink-0 ring-1 ring-white/10" style={{ backgroundColor: getHeatColor(sets(group)) }}></span>
            <span className="text-neutral-400">{group}</span>
            <span className="text-neutral-300 ml-auto">{sets(group)}</span>
          </div>
        ))}
        <div className="col-span-2 mt-2 pt-2 border-t border-neutral-800 text-[10px] text-neutral-600 leading-relaxed">
          Renk yoğunluğu haftalık set hacmine göre değişir: gri (çalışılmadı) → sarı → turuncu → kırmızı (çok yüksek hacim).
        </div>
      </div>
    </div>
  );
}
