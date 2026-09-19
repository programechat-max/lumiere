// Lumiere planlayıcı — profil verisinden kişiselleştirilmiş beslenme hedefleri,
// haftalık antrenman spliti ve öğün planı üretir. Tamamen istemci tarafında
// çalışır; program anında hazır olur. AI koç (backend /api/workout/program/
// generate) ayrıca arka planda daha detaylı program üretir, gelince değişir.
import type { MacroTargets } from './types';

/** Backend antrenman programı sözleşmesi (day_name TR hafta günü olmalı —
 *  programFor gün adına göre eşleştirir). */
export interface BackendProgram {
  id: number;
  day_name: string;
  exercises: Array<{ name: string; target_sets: number; target_reps: string; muscle_group?: string | null }>;
}

export interface PlannerInput {
  gender: string;   // 'Kadın' | 'Erkek'
  age: number;
  heightCm: number;
  weightKg: number;
  targetWeightKg: number;
  goal: string;     // 'Yağ yakımı + kas koruma' | 'Kas kazanımı' | 'Form koruma'
  level: string;    // 'Başlangıç' | 'Orta seviye' | 'İleri seviye'
  days: number;     // haftada 2..6 antrenman
  diet: string;     // 'Dengeli' | 'Akdeniz' | 'Vejetaryen' | 'Vegan' | 'Keto'
}

export interface NutritionPlan {
  bmr: number;
  tdee: number;
  strategy: string;
  targets: MacroTargets;
}

/* ---------- BESLENME HESABI (Mifflin-St Jeor) ---------- */
const ACTIVITY_FACTOR: Record<number, number> = { 1: 1.25, 2: 1.35, 3: 1.45, 4: 1.55, 5: 1.625, 6: 1.7 };

export function computeNutrition(p: PlannerInput): NutritionPlan {
  const male = p.gender !== 'Kadın';
  const bmr = Math.round(10 * p.weightKg + 6.25 * p.heightCm - 5 * p.age + (male ? 5 : -161));
  const tdee = Math.round(bmr * (ACTIVITY_FACTOR[Math.min(6, Math.max(1, p.days))] ?? 1.45));

  let calories = tdee;
  let strategy = 'Kilo koruma · kalori dengesi';
  if (p.goal.startsWith('Yağ')) {
    calories = Math.round(tdee * 0.82);
    strategy = `Günlük ${tdee - calories} kcal açık · haftada ~${((tdee - calories) * 7 / 7700).toFixed(1)} kg yağ`;
  } else if (p.goal.startsWith('Kas')) {
    calories = Math.round(tdee * 1.1);
    strategy = `Günlük ${calories - tdee} kcal fazlalık · temiz hacim`;
  }
  const floor = male ? 1500 : 1300;
  if (calories < floor) calories = floor;

  const keto = p.diet === 'Keto';
  let proteinPerKg = p.goal.startsWith('Yağ') ? 2.0 : p.goal.startsWith('Kas') ? 1.8 : 1.6;
  if (p.diet === 'Vejetaryen' || p.diet === 'Vegan') proteinPerKg = Math.max(1.5, proteinPerKg - 0.2);
  const refWeight = Math.min(p.weightKg, Math.max(p.targetWeightKg, p.weightKg * 0.7));
  const protein = Math.round(refWeight * proteinPerKg);

  let fats: number;
  let carbs: number;
  if (keto) {
    carbs = 30;
    fats = Math.max(60, Math.round((calories - carbs * 4 - protein * 4) / 9));
  } else {
    fats = Math.round((calories * 0.27) / 9);
    carbs = Math.max(80, Math.round((calories - protein * 4 - fats * 9) / 4));
  }
  return { bmr, tdee, strategy, targets: { calories, protein, carbs, fats } };
}

/* ---------- ANTRENMAN SPLITİ ---------- */
type ExDef = { name: string; muscle: string };

const LIB: Record<string, ExDef[]> = {
  Göğüs: [{ name: 'Bench Press', muscle: 'Göğüs' }, { name: 'Incline Dumbbell Press', muscle: 'Göğüs' }, { name: 'Cable Fly', muscle: 'Göğüs' }, { name: 'Şınav', muscle: 'Göğüs' }],
  Sırt: [{ name: 'Lat Pulldown', muscle: 'Sırt' }, { name: 'Barbell Row', muscle: 'Sırt' }, { name: 'Seated Cable Row', muscle: 'Sırt' }, { name: 'Yardımcı Barfiks', muscle: 'Sırt' }],
  Bacak: [{ name: 'Squat', muscle: 'Bacak' }, { name: 'Leg Press', muscle: 'Bacak' }, { name: 'Rumen Deadlift', muscle: 'Bacak' }, { name: 'Lunge', muscle: 'Bacak' }, { name: 'Leg Curl', muscle: 'Bacak' }, { name: 'Calf Raise', muscle: 'Bacak' }],
  Omuz: [{ name: 'Overhead Press', muscle: 'Omuz' }, { name: 'Lateral Raise', muscle: 'Omuz' }, { name: 'Face Pull', muscle: 'Omuz' }],
  Kol: [{ name: 'Barbell Curl', muscle: 'Kol' }, { name: 'Hammer Curl', muscle: 'Kol' }, { name: 'Triceps Pushdown', muscle: 'Kol' }, { name: 'Skull Crusher', muscle: 'Kol' }],
  Core: [{ name: 'Plank', muscle: 'Core' }, { name: 'Hanging Leg Raise', muscle: 'Core' }, { name: 'Cable Crunch', muscle: 'Core' }, { name: 'Russian Twist', muscle: 'Core' }],
  Kardiyo: [{ name: 'Tempolu Yürüyüş', muscle: 'Kardiyo' }, { name: 'Bisiklet', muscle: 'Kardiyo' }, { name: 'Koşu Bandı HIIT', muscle: 'Kardiyo' }],
};

function pick(muscle: string, n: number, offset = 0): ExDef[] {
  const list = LIB[muscle] ?? [];
  const out: ExDef[] = [];
  for (let i = 0; i < n && list.length; i++) out.push(list[(offset + i) % list.length]);
  return out;
}

function rx(level: string, goal: string, compound: boolean): { sets: number; reps: string } {
  if (level === 'Başlangıç') return compound ? { sets: 3, reps: '10-12' } : { sets: 3, reps: '12-15' };
  if (level === 'İleri seviye') return compound ? { sets: 5, reps: goal.startsWith('Kas') ? '6-8' : '8-10' } : { sets: 4, reps: '10-12' };
  return compound ? { sets: 4, reps: '8-12' } : { sets: 3, reps: '12-15' };
}

function dayProgram(id: number, dayName: string, blocks: Array<[string, number]>, p: PlannerInput, offsetBase = 0): BackendProgram {
  let offset = offsetBase;
  const exercises: BackendProgram['exercises'] = [];
  blocks.forEach(([muscle, count]) => {
    pick(muscle, count, offset).forEach((e) => {
      const compound = ['Squat', 'Bench Press', 'Overhead Press', 'Barbell Row', 'Rumen Deadlift', 'Leg Press'].includes(e.name);
      const r = rx(p.level, p.goal, compound);
      exercises.push({ name: e.name, target_sets: r.sets, target_reps: r.reps, muscle_group: e.muscle });
      offset += 1;
    });
  });
  if (p.goal.startsWith('Yağ')) {
    const cardio = pick('Kardiyo', 1, offsetBase)[0];
    if (cardio) exercises.push({ name: cardio.name, target_sets: 1, target_reps: '20 dk', muscle_group: 'Kardiyo' });
  }
  return { id, day_name: dayName, exercises };
}
const DAY_TR = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'];

/** 7 günlük split üretir; dinlenme günleri boş exercises ile gelir
 *  (programFor bunu "dinlenme" olarak gösterir). */
export function buildWeeklySplit(p: PlannerInput): BackendProgram[] {
  const d = Math.min(6, Math.max(2, p.days));
  const rest = (id: number, i: number): BackendProgram => ({ id, day_name: DAY_TR[i], exercises: [] });

  // şablonlar: [günIndex, bloklar] — bloklar [kas grubu, hareket sayısı]
  const templates: Record<number, Array<[number, Array<[string, number]>]>> = {
    2: [
      [0, [['Bacak', 2], ['Göğüs', 2], ['Sırt', 2], ['Core', 1]]],
      [3, [['Göğüs', 2], ['Sırt', 2], ['Bacak', 2], ['Omuz', 1]]],
    ],
    3: [
      [0, [['Bacak', 3], ['Göğüs', 2], ['Core', 2]]],
      [2, [['Göğüs', 2], ['Sırt', 3], ['Omuz', 1]]],
      [4, [['Sırt', 2], ['Bacak', 2], ['Kol', 2], ['Core', 1]]],
    ],
    4: [
      [0, [['Göğüs', 2], ['Sırt', 2], ['Omuz', 2], ['Kol', 1]]],
      [1, [['Bacak', 4], ['Core', 2]]],
      [3, [['Göğüs', 2], ['Sırt', 2], ['Omuz', 2], ['Kol', 1]]],
      [4, [['Bacak', 4], ['Core', 2]]],
    ],
    5: [
      [0, [['Göğüs', 3], ['Omuz', 2], ['Kol', 2]]],
      [1, [['Sırt', 3], ['Kol', 2], ['Core', 1]]],
      [3, [['Bacak', 4], ['Core', 2]]],
      [4, [['Göğüs', 2], ['Sırt', 3], ['Omuz', 1]]],
      [5, [['Bacak', 2], ['Core', 2], ['Kardiyo', 1]]],
    ],
    6: [
      [0, [['Göğüs', 3], ['Omuz', 2], ['Kol', 2]]],
      [1, [['Sırt', 3], ['Kol', 2], ['Core', 1]]],
      [2, [['Bacak', 4], ['Core', 2]]],
      [3, [['Göğüs', 2], ['Omuz', 3], ['Kol', 1]]],
      [4, [['Sırt', 3], ['Kol', 2], ['Core', 1]]],
      [5, [['Bacak', 3], ['Omuz', 1], ['Kardiyo', 1]]],
    ],
  };

  const tpl = templates[d];
  const out: BackendProgram[] = [];
  let id = 1;
  for (let i = 0; i < 7; i++) {
    const hit = tpl.find(([day]) => day === i);
    out.push(hit ? dayProgram(id++, DAY_TR[i], hit[1], p, i) : rest(id++, i));
  }
  return out;
}

export function splitLabel(days: number): string {
  return { 2: 'Full Body · 2 seans', 3: 'Full Body · 3 seans', 4: 'Üst / Alt bölme', 5: 'İtiş-Çekiş-Bacak + 2 seans', 6: 'Push / Pull / Legs x2' }[Math.min(6, Math.max(2, days))] ?? 'Full Body';
}

/* ---------- BESLENME PLANI ŞABLONU ---------- */
export interface MealItem { time: string; tag: string; name: string; detail: string; calories: number; protein: number }

type MealTpl = Array<{ name: string; detail: string }>;

const MEALS: Record<string, MealTpl> = {
  Dengeli: [
    { name: 'Yulaf Kasesi', detail: 'Yulaf + muz + fıstık ezmesi + whey' },
    { name: 'Izgara Tavuk Tabak', detail: 'Tavuk göğsü + bulgur + mevsim salata' },
    { name: 'Yoğurt + Granola', detail: 'Süzme yoğurt + granola + bal + ceviz' },
    { name: 'Somon Akşam', detail: 'Fırında somon + kinoa + brokoli' },
  ],
  Akdeniz: [
    { name: 'Menemen + Tam Buğday', detail: 'Yumurta + domates + zeytinyağı + ekmek' },
    { name: 'Izgara Balık', detail: 'Levrek + zeytinyağlı semizotu + tam buğday' },
    { name: 'Humus & Sebze', detail: 'Humus + çiğ sebze çubukları + zeytin' },
    { name: 'Zeytinyağlı Tavuk', detail: 'Tavuk + patlıcan + bulgur pilavı + yoğurt' },
  ],
  Vejetaryen: [
    { name: 'Peynirli Yulaf', detail: 'Yulaf + lor peyniri + muz + badem' },
    { name: 'Nohut Bowl', detail: 'Fırında nohut + kinoa + avokado + roka' },
    { name: 'Protein Smoothie', detail: 'Süt + whey + muz + yulaf + tarçın' },
    { name: 'Sebzeli Omlet', detail: '3 yumurta + kaşar + mantar + füme değil tost ekmeği' },
  ],
  Vegan: [
    { name: 'Chia Kasesi', detail: 'Chia + badem sütü + muz + fıstık ezmesi' },
    { name: 'Mercimek Bowl', detail: 'Kırmızı mercimek + kinoa + tahin sos' },
    { name: 'Soya Yoğurt', detail: 'Soya yoğurt + granola + chia + çilek' },
    { name: 'Tofu Sote', detail: 'Tofu + sebzeli sote + esmer pirinç' },
  ],
  Keto: [
    { name: 'Keto Omlet', detail: '3 yumurta + avokado + kaşar + tereyağı' },
    { name: 'Tavuk Salata', detail: 'Tavuk göğsü + zeytinyağı + yeşillik + parmesan' },
    { name: 'Kuruyemiş Tabak', detail: 'Ceviz + badem + peynir + zeytin' },
    { name: 'Somon + Avokado', detail: 'Somon + avokado + tereyağlı sebzeler' },
  ],
};

const SLOTS: Array<[string, string, number]> = [
  ['08:30', 'Kahvaltı', 0.27],
  ['13:00', 'Öğle', 0.31],
  ['16:30', 'Ara öğün', 0.14],
  ['19:30', 'Akşam', 0.28],
];

export function buildMealPlan(p: PlannerInput, targets: MacroTargets): MealItem[] {
  const tpl = MEALS[p.diet] ?? MEALS.Dengeli;
  return SLOTS.map(([time, tag, share], i) => {
    const kcal = Math.round((targets.calories * share) / 10) * 10;
    return {
      time,
      tag,
      name: tpl[i]?.name ?? 'Öğün',
      detail: tpl[i]?.detail ?? '',
      calories: kcal,
      protein: Math.round(targets.protein * share),
    };
  });
}

