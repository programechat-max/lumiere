// Lumiere store — UI ekran sözleşmesini koruyarak gerçek backend'e bağlar
// (/api/profile, /api/nutrition/*, /api/workout/*, /api/chat/*, /api/metrics,
// /api/progress/charts). İstekler apiClient (Bearer + 401 yenileme + timeout),
// kimlik doğrulama authService (/api/v1/auth) üzerinden yürür.
//
// Not: Adım sayacı cihaz ivmeölçerinden beslenen gerçek pedometre motoruyla
// (lib/pedometer.ts) çalışır ve localStorage'da kalıcıdır; uyku kayıtları
// /api/metrics ile senkronize edilir.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiFetch } from '../services/apiClient';
import * as authService from '../services/authService';
import { pedometer } from './pedometer';
import type { BackendProgram } from './planner';
import type { BodyCompositionSummary, CoachMessage, DayProgram, DayRecord, ExerciseLog, MacroTargets, MealLog, Profile } from './types';
import { isFuture, shiftISO, todayISO, uid } from './utils';

const VITALS_KEY = 'lumiere.vitals.v1';
const DONE_KEY = 'lumiere.done.v1';
const CHECKIN_KEY = 'lumiere.checkin.v1';
const ONBOARD_KEY = 'lumiere.onboarded.v1';
const STREAK_KEY = 'lumiere.streak.v1';

type VitalsPatch = { steps?: number; waterMl?: number; sleepHours?: number; sleepQuality?: number; mood?: number; energy?: number };
type Vitals = { steps: number; waterMl: number; sleepHours: number; sleepQuality?: number; mood?: number; energy?: number };
type VitalsMap = Record<string, Vitals>;
type MealsMap = Record<string, MealLog[]>;
type WorkoutMap = Record<string, ExerciseLog[]>;
type WeightMap = Record<string, number>;
type MacroTotals = Record<string, { calories: number; protein: number; carbs: number; fats: number }>;
/** Sabah check-in durumu: gün -> 'done' | 'snoozed' */
type CheckinMap = Record<string, 'done' | 'snoozed'>;
export type { BackendProgram };

const WEEKDAY_TR = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'];
const WEEKDAY_EN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export const DEFAULT_PROFILE: Profile = {
  name: 'Sporcu',
  goal: 'Form koruma',
  level: 'Orta seviye',
  gender: '',
  age: 27,
  heightCm: 175,
  currentWeight: 75,
  targetWeight: 70,
  activity: 'Orta hareketli',
  diet: 'Dengeli',
  workoutDays: 3,
  targets: { calories: 2200, protein: 150, carbs: 220, fats: 65 },
  memberSince: null as unknown as string,
  streak: 0,
};

function readJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch { return fallback; }
}
function writeJSON(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* noop */ }
}

function timeLabel(isoDateTime?: string | null): string {
  try {
    if (!isoDateTime) return '';
    const d = new Date(isoDateTime);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

function num(v: unknown, fallback = 0): number {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number);
  return typeof n === 'number' && Number.isFinite(n) ? n : fallback;
}

function mapBackendMeal(l: Record<string, unknown>): MealLog {
  return {
    id: String(l.id ?? uid('meal')),
    name: String(l.meal_name ?? l.name ?? 'Öğün'),
    calories: Math.round(num(l.calories)),
    protein: Math.round(num(l.protein ?? l.target_protein)),
    carbs: Math.round(num(l.carbs ?? l.target_carbs)),
    fats: Math.round(num(l.fats ?? l.target_fat)),
    time: String(l.time_target ?? ''),
  };
}

function groupLogsIntoMap(iso: string, logs: Array<Record<string, unknown>>, set: React.Dispatch<React.SetStateAction<WorkoutMap>>) {
  const byExercise = new Map<string, ExerciseLog>();
  logs.forEach((l) => {
    const name = String(l.exercise_name ?? 'Hareket');
    if (!byExercise.has(name)) byExercise.set(name, { name, muscle: 'Genel', sets: [] });
    byExercise.get(name)!.sets.push({ kg: num(l.weight_lifted), reps: Math.round(num(l.reps_done)) });
  });
  const list = [...byExercise.values()].map((e) => ({ ...e, sets: e.sets.slice().sort((a, b) => a.kg - b.kg) }));
  set((prev) => ({ ...prev, [iso]: list }));
}

function bumpStreak() {
  try {
    const t = todayISO();
    const state = readJSON<{ last?: string; count: number }>(STREAK_KEY, { count: 0 });
    if (state.last === t) return;
    writeJSON(STREAK_KEY, { last: t, count: (state.count ?? 0) + 1 });
  } catch { /* noop */ }
}

export function useLumiereStore() {
  const [profile, setProfileState] = useState<Profile>(DEFAULT_PROFILE);
  const [onboarded, setOnboarded] = useState<boolean>(() => readJSON(ONBOARD_KEY, false));
  const [selectedDate, setSelectedDate] = useState<string>(todayISO());
  const [vitalsMap, setVitalsMap] = useState<VitalsMap>(() => readJSON(VITALS_KEY, {}));
  const [mealsMap, setMealsMap] = useState<MealsMap>({});
  const [workoutMap, setWorkoutMap] = useState<WorkoutMap>({});
  const [weightMap, setWeightMap] = useState<WeightMap>({});
  const [macroHistory, setMacroHistory] = useState<MacroTotals>({});
  const [programs, setPrograms] = useState<BackendProgram[]>([]);
  const [chat, setChat] = useState<CoachMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatTyping, setChatTyping] = useState(false);
  const [doneMap, setDoneMap] = useState<Record<string, Record<string, boolean>>>(() => readJSON(DONE_KEY, {}));
  const [regenerating, setRegenerating] = useState(false);
  const loadedDaysRef = useRef<Set<string>>(new Set());
  const bootstrappedRef = useRef(false);

  const [checkinMap, setCheckinMap] = useState<CheckinMap>(() => readJSON<CheckinMap>(CHECKIN_KEY, {}));

  // Onboarding sırasında çekilen vücut videosunun AI analiz sonucu.
  // Plan uygulanırken /api/onboarding/complete ile kalıcı hafızaya yazılır
  // (build_system_prompt -> onboarding_video_analysis kategorisi), böylece
  // antrenman programı üretimi gerçekten bu analizi temel alır.
  const [onboardingVideo, setOnboardingVideo] = useState<Record<string, unknown> | null>(null);

  // Onboarding "Vücut Analizi" adımında cihaz çıktısından girilen ilk ölçüm.
  // Plan uygulanırken /api/onboarding/complete ile kalıcı ilk kayda dönüşür ve
  // Kişisel Bilgiler sayfasındaki gelişim serisinin başlangıcı olur.
  const [onboardingBodyComposition, setOnboardingBodyComposition] = useState<Record<string, number | string | null> | null>(null);

  // Kişisel Bilgiler sayfasının sunucudan gelen özeti: güncel değerler, Jarvis
  // kaynaklı değişim rozetleri (renk), segmentel dağılım ve haftalık seri.
  const [bodyComposition, setBodyComposition] = useState<BodyCompositionSummary | null>(null);
  const [bodyCompositionBusy, setBodyCompositionBusy] = useState(false);

  useEffect(() => writeJSON(VITALS_KEY, vitalsMap), [vitalsMap]);
  useEffect(() => writeJSON(DONE_KEY, doneMap), [doneMap]);
  useEffect(() => writeJSON(CHECKIN_KEY, checkinMap), [checkinMap]);

  // Gerçek adım sayacı: cihaz ivmeölçerinden (DeviceMotion) beslenir.
  // Motor her adımı bildirir; bugünün toplamı vitalsMap'e işlenir ve
  // localStorage'da kalıcı tutulur (backend'de adım alanı yok).
  useEffect(() => {
    pedometer.setStepSink((delta) => {
      if (delta <= 0) return;
      setVitalsMap((prev) => {
        const iso = todayISO();
        const cur = prev[iso] ?? { steps: 0, waterMl: 0, sleepHours: 0 };
        return { ...prev, [iso]: { ...cur, steps: cur.steps + delta } };
      });
    });
    pedometer.autoStart();
    return () => pedometer.setStepSink(null);
  }, []);

  // Pedometre kalori hesabı için güncel kiloyu besle.
  useEffect(() => { pedometer.setUserWeight(profile.currentWeight); }, [profile.currentWeight]);

  const applyProfile = useCallback((p: Record<string, unknown>) => {
    const user = authService.getStoredUser();
    setProfileState((prev) => ({
      ...prev,
      name: String(user?.full_name ?? user?.name ?? prev.name),
      goal: String(p.goal ?? prev.goal),
      level: p.experience_months != null
        ? (num(p.experience_months) >= 24 ? 'İleri seviye' : num(p.experience_months) >= 6 ? 'Orta seviye' : 'Başlangıç')
        : prev.level,
      currentWeight: num(p.current_weight, prev.currentWeight),
      targetWeight: num(p.target_weight, prev.targetWeight),
      targets: {
        calories: Math.round(num(p.daily_calorie_target, prev.targets.calories)),
        protein: Math.round(num(p.daily_protein_target, prev.targets.protein)),
        carbs: Math.round(num(p.daily_carb_target, prev.targets.carbs)),
        fats: Math.round(num(p.daily_fat_target, prev.targets.fats)),
      },
      memberSince: user?.created_at ?? prev.memberSince,
      // STREAK_KEY altında { last, count } objesi saklanır — sayı okunmazsa
      // Math.max(...) NaN üretiyor ve arayüz "nan günlük seri" gösteriyordu.
      streak: Math.max(prev.streak, readJSON<{ count?: number }>(STREAK_KEY, { count: 0 }).count ?? 0),
    }));
    if (p.onboarding_completed != null) {
      setOnboarded(!!p.onboarding_completed);
      writeJSON(ONBOARD_KEY, !!p.onboarding_completed);
    }
  }, []);

  const bootstrap = useCallback(async () => {
    if (!authService.isAuthenticated()) return;
    if (bootstrappedRef.current) return;
    bootstrappedRef.current = true;

    // Profil + birleşik grafik verisi + program + sohbet geçmişi (paralel).
    void apiFetch('/api/profile', { timeoutMs: 60_000, retries: 2 })
      .then((p) => applyProfile(p as Record<string, unknown>))
      .catch(() => undefined);

    void apiFetch('/api/progress/charts', { timeoutMs: 60_000 })
      .then((c: Record<string, unknown>) => {
        const weights = Array.isArray(c.weight) ? c.weight : [];
        setWeightMap((prev) => {
          const next = { ...prev };
          weights.forEach((w: Record<string, unknown>) => { if (w.date && w.weight != null) next[String(w.date)] = num(w.weight); });
          return next;
        });
        const nutrition = c.nutrition as Record<string, Record<string, unknown>> | Array<Record<string, unknown>> | undefined;
        const macros: MacroTotals = {};
        if (nutrition && !Array.isArray(nutrition)) {
          Object.entries(nutrition).forEach(([iso, v]) => {
            macros[iso] = { calories: num(v.calories), protein: num(v.protein), carbs: num(v.carbs), fats: num(v.fats) };
          });
        } else if (Array.isArray(nutrition)) {
          nutrition.forEach((row) => {
            if (row?.date) macros[String(row.date)] = { calories: num(row.calories), protein: num(row.protein), carbs: num(row.carbs), fats: num(row.fats) };
          });
        }
        setMacroHistory(macros);
        if (c.targets) {
          const tg = c.targets as Record<string, unknown>;
          setProfileState((prev) => ({
            ...prev,
            targets: {
              calories: Math.round(num(tg.calories, prev.targets.calories)),
              protein: Math.round(num(tg.protein, prev.targets.protein)),
              carbs: prev.targets.carbs,
              fats: prev.targets.fats,
            },
          }));
        }
      })
      .catch(() => undefined);

    void apiFetch('/api/workout', { timeoutMs: 60_000 })
      .then((w: Record<string, unknown>) => {
        const progs = Array.isArray(w.programs) ? (w.programs as BackendProgram[]) : [];
        setPrograms(progs);
        const logs = Array.isArray(w.today_logs) ? (w.today_logs as Array<Record<string, unknown>>) : [];
        if (logs.length) groupLogsIntoMap(String(todayISO()), logs, setWorkoutMap);
      })
      .catch(() => undefined);

    void apiFetch('/api/metrics?days=60', { timeoutMs: 60_000 })
      .then((rows: Array<Record<string, unknown>>) => {
        if (!Array.isArray(rows)) return;
        setVitalsMap((prev) => {
          const next = { ...prev };
          rows.forEach((r) => {
            const iso = String(r.date ?? '').slice(0, 10);
            const sleep = num(r.sleep_hours, 0);
            if (!iso || sleep <= 0) return;
            if (!next[iso]) next[iso] = { steps: 0, waterMl: 0, sleepHours: sleep };
            else if (!next[iso].sleepHours) next[iso] = { ...next[iso], sleepHours: sleep };
          });
          return next;
        });
      })
      .catch(() => undefined);

    void apiFetch('/api/chat/history?limit=40', { timeoutMs: 60_000 })
      .then((rows: Array<Record<string, unknown>>) => {
        if (!Array.isArray(rows)) return;
        setChat(rows.map((r) => ({
          id: uid('c'),
          role: r.role === 'user' ? 'user' : 'coach',
          text: String(r.text ?? ''),
          time: timeLabel(String(r.created_at ?? '')),
          tag: r.role === 'user' ? undefined : 'Koç yanıtı',
        })));
      })
      .catch(() => undefined);
  }, [applyProfile]);

  // Seçili gün değişince o günün öğün + antrenman kayıtlarını getirir.
  const ensureDay = useCallback((iso: string) => {
    if (loadedDaysRef.current.has(iso) || isFuture(iso)) return;
    loadedDaysRef.current.add(iso);
    void apiFetch(`/api/nutrition/day?day=${iso}`, { timeoutMs: 45_000 })
      .then((d: Record<string, unknown>) => {
        const meals = Array.isArray(d.meals) ? (d.meals as Array<Record<string, unknown>>).map(mapBackendMeal) : [];
        setMealsMap((prev) => ({ ...prev, [iso]: meals }));
      })
      .catch(() => { loadedDaysRef.current.delete(iso); });
    void apiFetch(`/api/workout/day?day=${iso}`, { timeoutMs: 45_000 })
      .then((d: Record<string, unknown>) => {
        const logs = Array.isArray(d.logs) ? (d.logs as Array<Record<string, unknown>>) : [];
        groupLogsIntoMap(iso, logs, setWorkoutMap);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => { void bootstrap(); }, [bootstrap]);
  useEffect(() => { ensureDay(selectedDate); }, [selectedDate, ensureDay]);

  const vitalsFor = useCallback((iso: string): Vitals => vitalsMap[iso] ?? { steps: 0, waterMl: 0, sleepHours: 0 }, [vitalsMap]);

  const updateVitals = useCallback((iso: string, patch: VitalsPatch) => {
    setVitalsMap((prev) => {
      const clean: Vitals = { ...(prev[iso] ?? { steps: 0, waterMl: 0, sleepHours: 0 }) };
      if (patch.steps != null) clean.steps = Math.max(0, Math.round(patch.steps));
      if (patch.waterMl != null) clean.waterMl = Math.max(0, Math.min(8000, Math.round(patch.waterMl)));
      if (patch.sleepHours != null) clean.sleepHours = Math.max(0, Math.min(16, Math.round(patch.sleepHours * 10) / 10));
      if (patch.sleepQuality != null) clean.sleepQuality = patch.sleepQuality;
      if (patch.mood != null) clean.mood = patch.mood;
      if (patch.energy != null) clean.energy = patch.energy;
      return { ...prev, [iso]: clean };
    });
    // Uyku kaydını backend'e senkronize et (BodyMetric.sleep_hours).
    if (patch.sleepHours != null) {
      void apiFetch('/api/metrics', {
        method: 'POST',
        body: JSON.stringify({ sleep_hours: Math.max(0, Math.min(16, Math.round(patch.sleepHours * 10) / 10)) }),
      }).catch(() => undefined);
    }
    bumpStreak();
  }, []);

  const mealsFor = useCallback((iso: string): MealLog[] => {
    if (mealsMap[iso]) return mealsMap[iso];
    // Gün detayı henüz çekilmediyse grafikler için gün toplamını tek kayıt olarak yansıt.
    const totals = macroHistory[iso];
    if (totals && (totals.calories > 0 || totals.protein > 0)) {
      return [{
        id: `agg-${iso}`, name: 'Günün öğünleri',
        calories: Math.round(totals.calories), protein: Math.round(totals.protein),
        carbs: Math.round(totals.carbs), fats: Math.round(totals.fats), time: '',
      }];
    }
    return [];
  }, [mealsMap, macroHistory]);

  const workoutFor = useCallback((iso: string): ExerciseLog[] => workoutMap[iso] ?? [], [workoutMap]);

  const programFor = useCallback((iso: string): DayProgram | null => {
    const dow = (new Date(`${iso}T12:00:00`).getDay() + 6) % 7; // Mon=0
    const candidates = [WEEKDAY_TR[dow], WEEKDAY_EN[dow]];
    let prog = programs.find((p) => candidates.some((c) => p.day_name?.toLowerCase() === c.toLowerCase()));
    if (!prog && programs.length > 0) prog = programs[dow % programs.length];
    if (!prog || !prog.exercises?.length) return null;
    const done = doneMap[iso] ?? {};
    return {
      dayName: prog.day_name,
      focus: prog.day_name,
      duration: `${prog.exercises.reduce((s, e) => s + (e.target_sets ?? 3), 0)} set`,
      exercises: prog.exercises.map((e) => ({
        name: e.name,
        muscle: e.muscle_group || 'Genel',
        sets: e.target_sets ?? 3,
        reps: e.target_reps ?? '8-10',
        rest: '90 sn',
        done: !!done[e.name],
      })),
    };
  }, [programs, doneMap]);

  const addMeal = useCallback((iso: string, m: Omit<MealLog, 'id' | 'time'> & { time?: string }) => {
    const tempId = uid('meal');
    const time = m.time ?? new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
    setMealsMap((prev) => ({ ...prev, [iso]: [...(prev[iso] ?? []), { ...m, id: tempId, time }] }));
    bumpStreak();
    void apiFetch('/api/nutrition', {
      method: 'POST',
      body: JSON.stringify({ meal_name: m.name, calories: m.calories, protein: m.protein, carbs: m.carbs, fats: m.fats, time_target: time }),
      timeoutMs: 90_000,
    })
      .then((saved: Record<string, unknown>) => {
        const realId = String(saved.id ?? tempId);
        setMealsMap((prev) => ({ ...prev, [iso]: (prev[iso] ?? []).map((x) => (x.id === tempId ? { ...x, id: realId } : x)) }));
        setMacroHistory((prev) => ({
          ...prev,
          [iso]: {
            calories: (prev[iso]?.calories ?? 0) + m.calories,
            protein: (prev[iso]?.protein ?? 0) + m.protein,
            carbs: (prev[iso]?.carbs ?? 0) + m.carbs,
            fats: (prev[iso]?.fats ?? 0) + m.fats,
          },
        }));
      })
      .catch(() => undefined);
  }, []);

  // Backend'de öğün silme ucu yok — kayıt yalnızca yerelden kaldırılır.
  const removeMeal = useCallback((iso: string, id: string) => {
    setMealsMap((prev) => ({ ...prev, [iso]: (prev[iso] ?? []).filter((x) => x.id !== id) }));
  }, []);

  const addExercise = useCallback((iso: string, ex: ExerciseLog) => {
    setWorkoutMap((prev) => ({ ...prev, [iso]: [...(prev[iso] ?? []), ex] }));
    bumpStreak();
    const existing = (workoutMap[iso] ?? []).reduce((s, e) => s + e.sets.length, 0);
    ex.sets.forEach((s, i) => {
      void apiFetch('/api/workout/log', {
        method: 'POST',
        body: JSON.stringify({ exercise_name: ex.name, set_number: existing + i + 1, weight_lifted: s.kg, reps_done: s.reps }),
      }).catch(() => undefined);
    });
  }, [workoutMap]);

  const logWeight = useCallback((iso: string, kg: number) => {
    setWeightMap((prev) => ({ ...prev, [iso]: kg }));
    setProfileState((p) => (iso === todayISO() ? { ...p, currentWeight: kg } : p));
    void apiFetch('/api/metrics', { method: 'POST', body: JSON.stringify({ weight: kg }) }).catch(() => undefined);
  }, []);

  const setProfile = useCallback((patch: Partial<Profile>) => {
    setProfileState((prev) => ({ ...prev, ...patch }));
    const body: Record<string, unknown> = {};
    if (patch.goal != null) body.goal = patch.goal;
    if (patch.currentWeight != null) body.current_weight = patch.currentWeight;
    if (patch.targetWeight != null) body.target_weight = patch.targetWeight;
    if (patch.heightCm != null) body.height = patch.heightCm;
    if (patch.age != null) body.age = patch.age;
    if (patch.level != null) body.experience_months = patch.level === 'Başlangıç' ? 3 : patch.level === 'İleri seviye' ? 36 : 15;
    if (patch.activity != null) body.activity_level = patch.activity === 'Az hareketli' ? 'light' : patch.activity === 'Aktif' ? 'high' : patch.activity === 'Çok aktif' ? 'athlete' : 'moderate';
    if (patch.diet != null) body.dietary_notes = `Beslenme tercihi: ${patch.diet}`;
    if (patch.targets) {
      body.daily_calorie_target = patch.targets.calories;
      body.daily_protein_target = patch.targets.protein;
      body.daily_carb_target = patch.targets.carbs;
      body.daily_fat_target = patch.targets.fats;
    }
    if (Object.keys(body).length === 0) return;
    void apiFetch('/api/profile', { method: 'PUT', body: JSON.stringify(body) }).catch(() => undefined);
  }, []);

  /** Lokal üretilen 7 günlük programı hemen devreye alır; AI programı
   *  gelince setPrograms onu ezecek. */
  const applyLocalPrograms = useCallback((progs: BackendProgram[]) => {
    setPrograms(progs);
  }, []);

  interface CompleteOnboardingArgs {
    goal: string;
    level: string;
    weight: number;
    targetWeight?: number;
    targets?: MacroTargets;
    gender?: string;
    age?: number;
    heightCm?: number;
    diet?: string;
    days?: number;
    /** Onboarding vücut videosu analizi — /api/onboarding/complete ile kalıcı hafızaya yazılır. */
    videoAnalysis?: Record<string, unknown> | null;
    /** Onboarding "Vücut Analizi" adımı — kalıcı İLK ölçüm kaydı olur. */
    bodyComposition?: Record<string, number | string | null> | null;
  }

  const completeOnboarding = useCallback(async ({ goal, level, weight, targetWeight, targets, gender, age, heightCm, diet, days, videoAnalysis, bodyComposition }: CompleteOnboardingArgs) => {
    setProfileState((prev) => ({
      ...prev,
      goal, level,
      currentWeight: weight,
      ...(targetWeight != null ? { targetWeight } : {}),
      ...(targets ? { targets } : {}),
      ...(gender ? { gender } : {}),
      ...(age ? { age } : {}),
      ...(heightCm ? { heightCm } : {}),
      ...(diet ? { diet } : {}),
      ...(days ? { workoutDays: days } : {}),
    }));
    setOnboarded(true);
    writeJSON(ONBOARD_KEY, true);
    const body: Record<string, unknown> = { goal, current_weight: weight, onboarding_completed: true };
    if (targetWeight != null) body.target_weight = targetWeight;
    if (targets) {
      body.daily_calorie_target = targets.calories;
      body.daily_protein_target = targets.protein;
      body.daily_carb_target = targets.carbs;
      body.daily_fat_target = targets.fats;
    }
    if (age) body.age = age;
    if (heightCm) body.height = heightCm;
    if (level) body.experience_months = level === 'Başlangıç' ? 3 : level === 'İleri seviye' ? 36 : 15;
    if (days) body.activity_level = days >= 5 ? 'high' : days >= 4 ? 'moderate' : 'light';
    if (diet) body.dietary_notes = `Beslenme tercihi: ${diet}`;
    // Program üretiminden önce profil ve video hafızası kesinlikle yazılmış
    // olmalı; aksi halde ilk üretim, videoyu hiç görmeden çalışabiliyordu.
    await apiFetch('/api/onboarding/complete', {
      method: 'POST',
      body: JSON.stringify({
        ...body,
        video_analysis: videoAnalysis ?? undefined,
        // Vücut analizi adımı boş geçilmediyse ilk ölçüm kaydı burada oluşur;
        // Kişisel Bilgiler sayfasının "ilk kayıt tarihi" bu ölçümdür.
        body_composition: bodyComposition && Object.values(bodyComposition).some((v) => v != null && v !== '')
          ? bodyComposition
          : undefined,
      }),
      timeoutMs: 60_000,
    });
  }, []);

  /**
   * Kişisel Bilgiler sayfası için vücut kompozisyonu özetini çeker.
   * Sunucu; güncel değerleri, Jarvis kaynaklı değişim rozetlerini, segmentel
   * dağılımı ve haftalık karşılaştırma serisini tek yanıtta döner.
   */
  const fetchBodyComposition = useCallback(async () => {
    setBodyCompositionBusy(true);
    try {
      const res = await apiFetch('/api/body-composition', { timeoutMs: 30_000 });
      setBodyComposition(res as BodyCompositionSummary);
      return res as BodyCompositionSummary;
    } catch {
      // Ulaşılamazsa sayfa boş durum gösterir; kullanıcıya hata fırlatmayız.
      return null;
    } finally {
      setBodyCompositionBusy(false);
    }
  }, []);

  /**
   * Yeni ölçüm kaydeder. Girilen değerler ANINDA güncel değerlere işlenir:
   * sunucu kaydı yazıp (aynı gün için upsert) Jarvis yorumunu üretir ve
   * güncellenmiş özeti döner, biz de onu doğrudan state'e koyarız.
   */
  const addBodyComposition = useCallback(async (values: Record<string, number | string | null>) => {
    setBodyCompositionBusy(true);
    try {
      const res = await apiFetch('/api/body-composition', {
        method: 'POST',
        body: JSON.stringify(values),
        timeoutMs: 90_000,
        retries: 1,
      });
      setBodyComposition(res as BodyCompositionSummary);
      return res as BodyCompositionSummary;
    } finally {
      setBodyCompositionBusy(false);
    }
  }, []);

  const regenerateProgram = useCallback(async () => {
    setRegenerating(true);
    try {
      // KOK COZUM (502): Render free plan senkron AI istegini ~100 sn'de gateway'de
      // kesiyordu. Program uretimini arka plana (BackgroundTasks) tasiyip durumu
      // job endpoint'inden sorguluyoruz; boylece uzun AI uretimi HTTP'i bloklamaz.
      const start = await apiFetch('/api/workout/program/generate/async', {
        method: 'POST',
        timeoutMs: 30_000,
        retries: 1,
      });
      const taskId = (start as Record<string, unknown>)?.task_id as string | undefined;
      if (!taskId) throw new Error('Program üretimi başlatılamadı.');

      // Job tamamlanana dek (success/failure) kisa araliklarla durumu sorgula.
      const deadline = Date.now() + 240_000; // AI soguk baslangic + uretim payi
      let done = false;
      while (Date.now() < deadline && !done) {
        await new Promise((r) => setTimeout(r, 4000));
        const job = await apiFetch(`/api/v1/jobs/${taskId}`, { timeoutMs: 20_000, retries: 1 }) as Record<string, unknown>;
        const status = String(job?.status || '');
        if (status === 'success') { done = true; break; }
        if (status === 'failure') {
          throw new Error(String(job?.error_message || 'Program üretilemedi.'));
        }
      }
      if (!done) throw new Error('Program üretimi zaman aşımına uğradı; birazdan tekrar dene.');

      // Uretim bitti - guncel program listesini cek.
      const workout = await apiFetch('/api/workout', { timeoutMs: 30_000, retries: 1 }) as Record<string, unknown>;
      const list = workout?.programs;
      if (Array.isArray(list)) setPrograms(list as BackendProgram[]);
    } finally {
      setRegenerating(false);
    }
  }, []);

  const regenerateNutrition = useCallback(async () => {
    const plan = await apiFetch('/api/mealplan/generate', { method: 'POST', timeoutMs: 180_000, retries: 1 });
    const items = Array.isArray(plan) ? plan : (plan as Record<string, unknown>)?.meal_plan;
    if (Array.isArray(items)) {
      const iso = todayISO();
      setMealsMap((prev) => ({
        ...prev,
        [iso]: items.map((item: Record<string, unknown>) => ({
          id: String(item.id ?? uid('meal')),
          name: String(item.meal_name ?? item.name ?? 'Öğün'),
          calories: num(item.calories), protein: num(item.protein),
          carbs: num(item.carbs), fats: num(item.fats),
          time: String(item.time_target ?? item.time ?? ''),
        })),
      }));
    }
  }, []);

  /** İlk kurulumda programı genel uçtan değil knowledge-layer anket kapısından üretir. */
  const generateKnowledgePlans = useCallback(async (days: number, diet: string) => {
    setRegenerating(true);
    try {
      const [workoutResponse, nutritionResponse] = await Promise.all([
        apiFetch('/api/program-builder/workout', {
          method: 'POST',
          body: JSON.stringify({
            days_per_week: days,
            training_style: 'hypertrophy',
          }),
          timeoutMs: 180_000,
          retries: 1,
        }),
        apiFetch('/api/program-builder/nutrition', {
          method: 'POST',
          body: JSON.stringify({ diet_style: diet }),
          timeoutMs: 180_000,
          retries: 1,
        }),
      ]);

      const workoutList = (workoutResponse as Record<string, unknown>)?.workout_programs;
      if (Array.isArray(workoutList)) setPrograms(workoutList as BackendProgram[]);

      const mealList = (nutritionResponse as Record<string, unknown>)?.meal_plan;
      if (Array.isArray(mealList)) {
        const iso = todayISO();
        setMealsMap((prev) => ({
          ...prev,
          [iso]: mealList.map((item: Record<string, unknown>) => ({
            id: String(item.id ?? uid('meal')),
            name: String(item.meal_name ?? item.name ?? 'Öğün'),
            calories: num(item.calories), protein: num(item.protein),
            carbs: num(item.carbs), fats: num(item.fats),
            time: String(item.time_target ?? item.time ?? ''),
          })),
        }));
      }
    } finally {
      setRegenerating(false);
    }
  }, []);

  const sendChat = useCallback((text: string) => {
    const clean = text.trim();
    if (!clean || chatTyping) return;
    const now = new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
    setChat((prev) => [...prev, { id: uid('u'), role: 'user', text: clean, time: now }]);
    setChatInput('');
    setChatTyping(true);
    void apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message: clean, session_id: 'default' }),
      timeoutMs: 120_000,
    })
      .then((res: Record<string, unknown>) => {
        const reply = String(res.jarvis_reply ?? 'Şu an cevap veremiyorum, tekrar dener misin?');
        setChat((prev) => [...prev, {
          id: uid('c'), role: 'coach', text: reply,
          time: new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }),
          tag: 'Koç yanıtı',
        }]);
      })
      .catch((err: Error) => {
        setChat((prev) => [...prev, {
          id: uid('c'), role: 'coach', text: `Bağlantı hatası: ${err.message}`,
          time: new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }),
        }]);
      })
      .finally(() => setChatTyping(false));
  }, [chatTyping]);

  const toggleDone = useCallback((iso: string, key: string) => {
    setDoneMap((prev) => ({ ...prev, [iso]: { ...(prev[iso] ?? {}), [key]: !(prev[iso]?.[key]) } }));
  }, []);

  /** Sabah check-in tamamlandı → güne işle ve seriyi ilerlet. */
  const markCheckinDone = useCallback((iso: string) => {
    setCheckinMap((prev) => ({ ...prev, [iso]: 'done' }));
    bumpStreak();
  }, []);

  /** "Şimdi değil" — bugün bir daha otomatik sorulmaz, akışta kart kalır. */
  const snoozeCheckin = useCallback((iso: string) => {
    setCheckinMap((prev) => ({ ...prev, [iso]: 'snoozed' }));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    bootstrappedRef.current = false;
    const user = await authService.login(email, password);
    await bootstrap();
    return user;
  }, [bootstrap]);

  const register = useCallback(async (fullName: string, email: string, password: string) => {
    bootstrappedRef.current = false;
    const user = await authService.register(fullName, email, password);
    await bootstrap();
    setOnboarded(false);
    writeJSON(ONBOARD_KEY, false);
    return user;
  }, [bootstrap]);

  const logout = useCallback(async () => {
    await authService.logout();
    bootstrappedRef.current = false;
    loadedDaysRef.current = new Set();
    setProfileState(DEFAULT_PROFILE);
    setPrograms([]);
    setChat([]);
    setMealsMap({});
    setWorkoutMap({});
    setWeightMap({});
    setMacroHistory({});
    setOnboarded(false);
  }, []);

  const dayRecord = useCallback((iso: string): DayRecord => {
    const v = vitalsFor(iso);
    const meals = mealsFor(iso);
    return {
      iso,
      vitals: { steps: v.steps, waterMl: v.waterMl, sleepHours: v.sleepHours, sleepQuality: v.sleepQuality, mood: v.mood, energy: v.energy },
      meals,
      exercises: workoutFor(iso),
      program: programFor(iso),
      weight: weightMap[iso],
      checkinDone: (v.waterMl > 0 || v.sleepHours > 0 || meals.length > 0),
    };
  }, [vitalsFor, mealsFor, workoutFor, programFor, weightMap]);

  const last14 = useMemo(() => {
    const t = todayISO();
    return Array.from({ length: 14 }, (_, i) => shiftISO(t, -(13 - i))).map((iso) => dayRecord(iso));
  }, [dayRecord, mealsMap, workoutMap, vitalsMap, weightMap, macroHistory, programs, doneMap]);

  const weightSeries = useMemo(() => {
    const t = todayISO();
    const pts: Array<{ date: string; short: string; weight: number }> = [];
    const dates = [...new Set([...Object.keys(weightMap), t])].filter((d) => !isFuture(d)).sort();
    dates.forEach((iso) => {
      const w = weightMap[iso] ?? (iso === t ? profile.currentWeight : null);
      if (w == null) return;
      pts.push({ date: iso, short: iso.slice(8, 10) + '/' + iso.slice(5, 7), weight: w });
    });
    return pts;
  }, [weightMap, profile.currentWeight]);

  return {
    profile, setProfile,
    onboarded, setOnboarded: (v: boolean) => { setOnboarded(v); writeJSON(ONBOARD_KEY, v); },
    selectedDate, setSelectedDate,
    shiftSelectedDate: (d: number) => setSelectedDate((s) => shiftISO(s, d)),
    vitalsFor, updateVitals,
    mealsFor, addMeal, removeMeal,
    workoutFor, addExercise,
    logWeight, weightMap,
    dayRecord, last14, weightSeries,
    chat, chatInput, setChatInput, chatTyping, sendChat,
    doneMap, toggleDone,
    checkinMap, markCheckinDone, snoozeCheckIn: snoozeCheckin,
    onboardingVideo, applyOnboardingVideo: (v: Record<string, unknown> | null) => setOnboardingVideo(v),
    onboardingBodyComposition,
    applyOnboardingBodyComposition: (v: Record<string, number | string | null> | null) => setOnboardingBodyComposition(v),
    bodyComposition, bodyCompositionBusy, fetchBodyComposition, addBodyComposition,
    programFor,
    // backend ekstraları
    login, register, logout, completeOnboarding, applyLocalPrograms, regenerateProgram, regenerateNutrition, generateKnowledgePlans, regenerating, ensureDay,
  };
}

export type Store = ReturnType<typeof useLumiereStore>;
