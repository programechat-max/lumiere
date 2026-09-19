export type TabKey = 'flow' | 'coach' | 'daily' | 'workout' | 'nutrition' | 'progress' | 'profile';

/** Vücut kompozisyonu ölçümünün tek bir metriği (değişim + Jarvis renk kararı). */
export interface BodyCompositionMetric {
  key: string;
  label: string;
  group: string;
  group_label: string;
  unit: string;
  decimals: number;
  current: number | null;
  previous: number | null;
  delta: number | null;
  delta_label: string | null;
  /** Ok yönü: değişimin kendisi (arttı/azaldı). */
  direction: 'up' | 'down' | 'flat';
  /** Rozet rengi: YALNIZCA Jarvis yorumundan gelir. */
  tone: 'positive' | 'negative' | 'neutral';
}

export interface BodyCompositionGroup {
  key: string;
  label: string;
  metrics: BodyCompositionMetric[];
}

export interface BodyCompositionSegment {
  key: string;
  label: string;
  fat_percent: number | null;
  muscle_kg: number | null;
  fat_kg: number | null;
}

export interface BodyCompositionRecord {
  id: number;
  date: string;
  source?: string;
  review?: Record<string, unknown> | null;
  created_at?: string | null;
  note?: string | null;
  [metric: string]: unknown;
}

export interface BodyCompositionSummary {
  has_data: boolean;
  latest: BodyCompositionRecord | null;
  previous: BodyCompositionRecord | null;
  first_record_date: string | null;
  record_count: number;
  review: { sentiment?: string; summary?: string; highlights?: string[]; source?: string } | null;
  metrics: BodyCompositionMetric[];
  groups: BodyCompositionGroup[];
  segments: BodyCompositionSegment[];
  history: BodyCompositionRecord[];
}

export interface MacroTargets {
  calories: number;
  protein: number;
  carbs: number;
  fats: number;
}

export interface DayVitals {
  steps: number; // auto-calculated
  waterMl: number; // user input
  sleepHours: number; // user input
  sleepQuality?: number; // 1-5
  mood?: number; // 1-5
  energy?: number; // 1-5
}

export interface MealLog {
  id: string;
  name: string;
  calories: number;
  protein: number;
  carbs: number;
  fats: number;
  time: string;
  photo?: boolean;
}

export interface SetLog {
  kg: number;
  reps: number;
}

export interface ExerciseLog {
  name: string;
  muscle: string;
  sets: SetLog[];
}

export interface MealPlanItem {
  id: string;
  name: string;
  detail: string;
  calories: number;
  protein: number;
  time: string;
  done: boolean;
}

export interface WorkoutExercise {
  name: string;
  muscle: string;
  sets: number;
  reps: string;
  rest: string;
  done: boolean;
}

export interface DayProgram {
  dayName: string;
  focus: string;
  duration: string;
  exercises: WorkoutExercise[];
}

export interface CoachMessage {
  id: string;
  role: 'user' | 'coach';
  text: string;
  time: string;
  tag?: string;
}

export interface DayRecord {
  iso: string;
  vitals: DayVitals;
  meals: MealLog[];
  exercises: ExerciseLog[];
  program: DayProgram | null;
  weight?: number;
  checkinDone: boolean;
}

export interface Profile {
  name: string;
  goal: string;
  level: string;
  gender: string;        // 'Kadın' | 'Erkek' | '' (backend'te karşılığı yok, lokal)
  age: number;
  heightCm: number;
  currentWeight: number;
  targetWeight: number;
  activity: string;      // 'Az hareketli' | 'Orta hareketli' | 'Aktif' | 'Çok aktif'
  diet: string;          // 'Dengeli' | 'Akdeniz' | 'Vejetaryen' | 'Vegan' | 'Keto'
  workoutDays: number;   // haftada antrenman günü (lokal tercih)
  targets: MacroTargets;
  memberSince: string;
  streak: number;
}
