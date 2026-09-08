import { useState, useCallback, useRef, useEffect } from 'react';
import Login from './Login';
import Register from './Register';
import FlowScreen from './components/FlowScreen';
import SettingsMenu from './components/SettingsMenu';
import OnboardingWizard from './components/OnboardingWizard';
import ProgramBuilder from './components/ProgramBuilder';
import AdminPanel from './components/AdminPanel';
import ChatScreen from './components/screens/ChatScreen';
import DailyScreen from './components/screens/DailyScreen';
import WorkoutScreen from './components/screens/WorkoutScreen';
import NutritionScreen from './components/screens/NutritionScreen';
import ProgressScreen from './components/screens/ProgressScreen';
import BottomNav, { NAV_KEYS } from './components/lumiere/BottomNav';
import { API_BASE } from './config';
import * as authService from './services/authService';

/* eslint-disable react-hooks/set-state-in-effect */

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

export default function DashboardMaster() {
  const [memberSince, setMemberSince] = useState(() => {
    try {
      return authService.getStoredUser()?.created_at || null;
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
  const [showProgramBuilder, setShowProgramBuilder] = useState(false);
  const [programContext, setProgramContext] = useState(null);

  // Token varsa /api/status doğrulanana kadar "yükleniyor" göstermemiz gerekiyor;
  // aksi halde isSetupComplete henüz bilinmeden (varsayılan false) bir anlığına
  // yanlışlıkla onboarding ekranı gösterilir. Token yoksa zaten login'e düşülüyor.
  const [loading, setLoading] = useState(authService.isAuthenticated());
  const [activeTab, setActiveTab] = useState('flow');
  const activeTabRef = useRef('flow');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  // Kamera/mikrofon için kullanıcının kalıcı rıza kararı (/api/status'tan gelir).
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

  // Jarvis chat
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatSending, setChatSending] = useState(false);
  const chatEndRef = useRef(null);

  // Gelişim grafikleri
  const [chartData, setChartData] = useState(null);
  const [loadingCharts, setLoadingCharts] = useState(false);

  // Yemek fotoğrafı
  const [foodPhotoPreview, setFoodPhotoPreview] = useState(null);
  const [foodPhotoAnalyzing, setFoodPhotoAnalyzing] = useState(false);
  const [foodPhotoError, setFoodPhotoError] = useState('');
  const foodPhotoInputRef = useRef(null);

  const [statusError, setStatusError] = useState('');
  const isAdmin = ['ADMIN', 'SUPER_ADMIN'].includes((authService.getStoredUser()?.role || '').toUpperCase());
const navigateToTab = useCallback((nextTab) => {
    if (!NAV_KEYS.includes(nextTab) && nextTab !== 'progress') return;
    const previousTab = activeTabRef.current;
    if (previousTab === nextTab) return;
    activeTabRef.current = nextTab;
    setActiveTab(nextTab);
  }, []);

const handleQuickAction = useCallback((action) => {
    // Flow ekranından gelen hızlı aksiyonlar → ilgili sekmeye yönlendir
    console.log('[FlowScreen] Quick action:', action);
  }, []);

  const handleLogout = () => {
    authService.logout().catch(() => {});
    setCurrentPage('login');
  };

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
const fetchDashboardData = useCallback(async () => {
    const token = authService.getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }

    try {
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
        const errText = await statusRes.text().catch(() => '');
        console.error('[Dashboard] Status error:', statusRes.status, errText);
        if (statusRes.status === 401) {
          handleIfSessionExpired(statusRes);
        } else {
          setIsSetupComplete(false);
          setStatusError('');
        }
        return;
      }
      setStatusError('');

      const statusData = await statusRes.json();
      setIsSetupComplete(!!statusData.is_setup_complete);
      setPermissions({
        camera: statusData.camera_permission_granted ?? null,
        microphone: statusData.microphone_permission_granted ?? null,
      });

      if (statusData.is_setup_complete) {
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
      console.error('[Dashboard] Backend bağlantı hatası:', error);
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
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000);
    return () => clearInterval(interval);
  }, [fetchDashboardData, currentPage]);

  // Her sekme yeni bir ekran gibi en üstten başlar; özellikle iPhone'da uzun
  // bir akıştan sonra sekme değiştirilince eski scroll konumu taşınmaz.
  useEffect(() => {
    if (!isSetupComplete || showProgramBuilder) return;
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }, [activeTab, isSetupComplete, showProgramBuilder]);

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
      console.error('Günlük pencere hatası:', error);
    } finally {
      setLoadingDaily(false);
    }
  }, [authenticatedFetch]);

  useEffect(() => {
    if (activeTab === 'daily') {
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

  // Hedefler backend'deki profilden geliyor
  const targetCalories = profile?.daily_calorie_target || 2200;
  const targetProtein = profile?.daily_protein_target || 140;
  const latestWeight = metrics.length > 0 ? metrics[metrics.length - 1].weight : profile?.current_weight;
  const firstWeight = metrics.find((m) => m.weight)?.weight;
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
      <main className="hero-bg flex min-h-dvh flex-col items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 border-2 border-border border-t-primary rounded-full animate-spin" />
          <p className="eyebrow text-primary-glow">LUMIERE hazırlanıyor</p>
        </div>
      </main>
    );
  }

  // ==========================================
  // BAĞLANTI HATASI (durum bilinmiyor - onboarding'e YANLIŞLIKLA düşmeyelim)
  // ==========================================
  if (statusError) {
    return (
      <main className="hero-bg flex min-h-dvh flex-col items-center justify-center px-6 text-center">
        <p className="font-mono text-sm text-primary-glow mb-4 max-w-sm">{statusError}</p>
        <button
          onClick={() => { setLoading(true); setStatusError(''); fetchDashboardData(); }}
          className="ember ember-glow h-12 rounded-xl px-5 text-sm font-bold"
        >
          Tekrar Dene
        </button>
        <button
          onClick={handleLogout}
          className="mt-3 text-xs font-mono text-muted-foreground underline"
        >
          Çıkış yap ve tekrar giriş yap
        </button>
      </main>
    );
  }

  // ==========================================
  // KİLİTLİ EKRAN (VERİ YOKSA)
  // ==========================================
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
  // CANLI DASHBOARD (love repo app.tsx kabuğu)
  // ==========================================
  return (
    <div className="min-h-dvh bg-background">
      <div className="mx-auto min-h-dvh w-full max-w-md px-5 pb-28">
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
            isAdmin={isAdmin}
            onOpenAdmin={() => setAdminOpen(true)}
          />
        )}

        {activeTab === 'chat' && (
          <ChatScreen
            messages={chatMessages}
            input={chatInput}
            sending={chatSending}
            onInputChange={setChatInput}
            onSubmit={sendChatMessage}
            chatEndRef={chatEndRef}
          />
        )}

        {activeTab === 'daily' && (
          <DailyScreen
            selectedDate={selectedDate}
            onDateChange={setSelectedDate}
            shiftDate={shiftSelectedDate}
            loading={loadingDaily}
            nutrition={dailyNutrition}
            workout={dailyWorkout}
            heatmap={dailyHeatmap}
            profile={profile}
          />
        )}

        {activeTab === 'workout' && (
          <WorkoutScreen
            workout={workout}
            deloadStatus={deloadStatus}
            workoutError={workoutError}
            generatingProgram={generatingProgram}
            onGenerateProgram={generateWorkoutProgram}
            metrics={metrics}
          />
        )}

        {activeTab === 'nutrition' && (
          <NutritionScreen
            nutritionPlans={nutritionPlans}
            mealPlan={mealPlan}
            generatingPlan={generatingPlan}
            onRegenerateMealPlan={regenerateMealPlan}
            onDeleteMealPlan={deleteMealPlan}
            foodPhotoPreview={foodPhotoPreview}
            foodPhotoAnalyzing={foodPhotoAnalyzing}
            foodPhotoError={foodPhotoError}
            foodPhotoInputRef={foodPhotoInputRef}
            onFileSelect={analyzeFoodPhoto}
            onConfirmPhoto={confirmFoodPhoto}
            onCancelPhoto={() => { setFoodPhotoPreview(null); setFoodPhotoError(''); }}
            profile={profile}
          />
        )}

        {activeTab === 'progress' && (
          <ProgressScreen
            chartData={chartData}
            loadingCharts={loadingCharts}
            latestWeight={latestWeight}
            weightDelta={weightDelta}
            metrics={metrics}
            workout={workout}
            insights={insights}
            analyzing={analyzing}
            weightInput={weightInput}
            savingWeight={savingWeight}
            onWeightInputChange={setWeightInput}
            onSubmitWeight={submitWeight}
            onRunAnalysis={runWeeklyAnalysis}
            targetCalories={targetCalories}
            targetProtein={targetProtein}
          />
        )}

        <SettingsMenu
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          onLogout={handleLogout}
          permissions={permissions}
          onPermissionsChanged={fetchDashboardData}
        />
        <AdminPanel open={adminOpen} onClose={() => setAdminOpen(false)} />
      </div>
      <BottomNav activeTab={activeTab} onNavigate={navigateToTab} />
    </div>
  );
}