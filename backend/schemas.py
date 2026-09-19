from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, List, Optional
from datetime import date, datetime
# NOT: Python 3.14 (PEP 649) anotasyonları tembel çözer ve sınıf gövdesindeki
# adları önceliklendirir. Alan adı ile tip adı aynı olduğunda ('date: date')
# varsayılan değerli alanlarda tip yanlışlıkla None'a çözülür; bu yüzden
# 'date' alanının varsayılan aldığı şemalarda bu takma ad kullanılır.
from datetime import date as date_cls
# --- HESAP / AUTH ŞEMALARI ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    # Kayıt sırasında seçilen üyelik planı (FREE|PRO|ELITE|ELITE_PLUS) — opsiyonel,
    # gönderilmezse FREE kabul edilir.
    preferred_plan: Optional[str] = "FREE"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    created_at: datetime
    role: Optional[str] = "USER"

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- PROFİL ŞEMALARI ---
class UserProfileBase(BaseModel):
    age: Optional[int] = None
    height: Optional[float] = None
    current_weight: Optional[float] = None
    target_weight: Optional[float] = None
    goal: Optional[str] = None
    target_physique: Optional[str] = None
    experience_months: Optional[int] = None
    focus_muscle_group: Optional[str] = None
    activity_level: Optional[str] = None
    dietary_notes: Optional[str] = None
    schedule_notes: Optional[str] = None
    injury_notes: Optional[str] = None
    daily_calorie_target: Optional[float] = None
    daily_protein_target: Optional[float] = None
    daily_carb_target: Optional[float] = None
    daily_fat_target: Optional[float] = None
    camera_permission_granted: Optional[bool] = None
    microphone_permission_granted: Optional[bool] = None
    preferred_plan: Optional[str] = None
    onboarding_completed: Optional[bool] = None

class UserProfileResponse(UserProfileBase):
    id: int
    class Config:
        from_attributes = True


class OnboardingCompleteRequest(UserProfileBase):
    """Temel profil ile birlikte onboarding medya analizlerinin kalıcı aktarımı.

    'body_composition' onboarding'deki "Vücut Analizi" adımında girilen ilk
    ölçümdür (video analizinden ÖNCE toplanır); kayıt tarihi kullanıcının ilk
    kişisel bilgi kaydı olur ve gelişim serisinin başlangıcı sayılır.
    """
    video_analysis: Optional[Dict[str, Any]] = None
    voice_analysis: Optional[Dict[str, Any]] = None
    body_composition: Optional[Dict[str, Any]] = None

# --- HAREKET VE PROGRAM ŞEMALARI ---
class ExerciseBase(BaseModel):
    name: str
    target_sets: int
    target_reps: str
    muscle_group: Optional[str] = None
    target_rpe: Optional[float] = None
    exercise_type: Optional[str] = None
    stretch_mediated: Optional[bool] = None
    unilateral: Optional[bool] = None
    equipment: Optional[str] = None
    technique_cue: Optional[str] = None
    progression_model: Optional[str] = None

class ExerciseCreate(ExerciseBase):
    pass

class ExerciseResponse(ExerciseBase):
    id: int
    program_id: int
    target_rpe: Optional[float] = None
    exercise_type: Optional[str] = None
    stretch_mediated: Optional[bool] = None
    unilateral: Optional[bool] = None
    equipment: Optional[str] = None
    technique_cue: Optional[str] = None
    progression_model: Optional[str] = None
    class Config:
        from_attributes = True

class WorkoutProgramBase(BaseModel):
    day_name: str
    is_active: bool = True

class WorkoutProgramCreate(WorkoutProgramBase):
    exercises: List[ExerciseCreate]

class WorkoutProgramResponse(WorkoutProgramBase):
    id: int
    exercises: List[ExerciseResponse]
    class Config:
        from_attributes = True

# --- ANTRENMAN LOG ŞEMALARI ---
class WorkoutLogCreate(BaseModel):
    exercise_name: str
    set_number: int = Field(ge=1)
    weight_lifted: float = Field(ge=0)
    reps_done: int = Field(ge=0)
    rpe: Optional[int] = Field(default=None, ge=1, le=10)

class WorkoutLogResponse(WorkoutLogCreate):
    id: int
    date: date
    class Config:
        from_attributes = True

# --- BESLENME LOG ŞEMALARI ---
class NutritionLogCreate(BaseModel):
    meal_name: str
    time_target: Optional[str] = None
    ingredients: Optional[str] = None
    protein: float = Field(default=0.0, ge=0)
    carbs: float = Field(default=0.0, ge=0)
    fats: float = Field(default=0.0, ge=0)
    calories: float = Field(default=0.0, ge=0)
    # FAZ 7 — doğrulama/mikro katmanı (opsiyonel, geriye uyumlu)
    verification_source: Optional[str] = None
    verified: Optional[bool] = False
    confidence: Optional[str] = None
    micros: Optional[dict] = None
    items_breakdown: Optional[list] = None

class NutritionLogResponse(NutritionLogCreate):
    id: int
    date: date
    class Config:
        from_attributes = True

# --- VÜCUT ÖLÇÜMÜ ŞEMALARI ---
class BodyMetricCreate(BaseModel):
    weight: Optional[float] = Field(default=None, ge=0)
    waist: Optional[float] = Field(default=None, ge=0)
    chest: Optional[float] = Field(default=None, ge=0)
    arm: Optional[float] = Field(default=None, ge=0)
    sleep_hours: Optional[float] = Field(default=None, ge=0)
    note: Optional[str] = None

class BodyMetricResponse(BodyMetricCreate):
    id: int
    date: date
    class Config:
        from_attributes = True

# --- VÜCUT KOMPOZİSYONU ŞEMALARI (Kişisel Bilgiler sayfası) ---
# Tüm alanlar opsiyonel: kullanıcı InBody benzeri cihaz çıktısından yalnızca
# okuyabildiği değerleri girer. Sıfır/negatif değer fiziksel olarak anlamsız
# olduğundan ge alanlarıyla elenir; üst sınır da saçma girişleri engeller.
def _body_kg():
    """0-400 kg aralığında opsiyonel gövde ölçüsü alanı.

    Field() nesnesini modül düzeyinde paylaşmak yerine her alan için yeni bir
    FieldInfo üretilir (Pydantic v2'de paylaşılan field nesneleri önerilmez).
    """
    return Field(default=None, ge=0, le=400)


class BodyCompositionBase(BaseModel):
    """Genel + segmentel vücut kompozisyonu alanları (hepsi opsiyonel)."""
    # Genel
    body_fat_percent: Optional[float] = Field(default=None, ge=0, le=100)
    total_fat_kg: Optional[float] = _body_kg()
    lean_mass_kg: Optional[float] = _body_kg()
    muscle_kg: Optional[float] = _body_kg()
    bone_mass_kg: Optional[float] = _body_kg()
    body_water_kg: Optional[float] = _body_kg()

    # Segmentel yağ oranı (%)
    right_leg_fat_percent: Optional[float] = Field(default=None, ge=0, le=100)
    left_leg_fat_percent: Optional[float] = Field(default=None, ge=0, le=100)
    right_arm_fat_percent: Optional[float] = Field(default=None, ge=0, le=100)
    left_arm_fat_percent: Optional[float] = Field(default=None, ge=0, le=100)
    trunk_fat_percent: Optional[float] = Field(default=None, ge=0, le=100)

    # Segmentel kas (kg)
    right_leg_muscle_kg: Optional[float] = _body_kg()
    left_leg_muscle_kg: Optional[float] = _body_kg()
    right_arm_muscle_kg: Optional[float] = _body_kg()
    left_arm_muscle_kg: Optional[float] = _body_kg()
    trunk_muscle_kg: Optional[float] = _body_kg()

    # Segmentel yağ (kg)
    right_leg_fat_kg: Optional[float] = _body_kg()
    left_leg_fat_kg: Optional[float] = _body_kg()
    right_arm_fat_kg: Optional[float] = _body_kg()
    left_arm_fat_kg: Optional[float] = _body_kg()
    trunk_fat_kg: Optional[float] = _body_kg()

    note: Optional[str] = None


class BodyCompositionCreate(BodyCompositionBase):
    """Yeni ölçüm isteği. 'date' verilmezse bugün kullanılır."""
    date: Optional[date_cls] = None
    source: Optional[str] = "manual"


class BodyCompositionResponse(BodyCompositionBase):
    id: int
    date: date
    source: Optional[str] = "manual"
    review: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True


class BodyCompositionMetric(BaseModel):
    """Tek bir metriğin güncel değeri + Jarvis kaynaklı renk/yön bilgisi."""
    key: str
    label: str
    group: str
    group_label: str
    unit: str
    decimals: int
    current: Optional[float] = None
    previous: Optional[float] = None
    delta: Optional[float] = None
    delta_label: Optional[str] = None
    direction: str = "flat"      # up | down | flat
    tone: str = "neutral"        # positive | negative | neutral (Jarvis yorumu)


class BodyCompositionGroup(BaseModel):
    key: str
    label: str
    metrics: List[BodyCompositionMetric]


class BodyCompositionSegment(BaseModel):
    key: str
    label: str
    fat_percent: Optional[float] = None
    muscle_kg: Optional[float] = None
    fat_kg: Optional[float] = None


class BodyCompositionSummary(BaseModel):
    """Kişisel Bilgiler sayfasının tek veri kaynağı."""
    has_data: bool
    latest: Optional[BodyCompositionResponse] = None
    previous: Optional[BodyCompositionResponse] = None
    first_record_date: Optional[date] = None
    record_count: int = 0
    review: Optional[Dict[str, Any]] = None
    metrics: List[BodyCompositionMetric] = []
    groups: List[BodyCompositionGroup] = []
    segments: List[BodyCompositionSegment] = []
    history: List[BodyCompositionResponse] = []


# --- HAFIZA / İÇGÖRÜ ŞEMALARI ---
class UserMemoryCreate(BaseModel):
    category: str = "note"
    content: str
    importance: Optional[int] = 5

class UserMemoryUpdate(BaseModel):
    content: Optional[str] = None
    category: Optional[str] = None
    importance: Optional[int] = None

class UserMemoryResponse(UserMemoryCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    keywords: Optional[str] = ""
    memory_key: Optional[str] = None
    access_count: Optional[int] = 0
    class Config:
        from_attributes = True


class CheckInRequest(BaseModel):
    mood: int = 3
    energy: int = 3
    sleep_quality: int = 3
    soreness: int = 2
    notes: Optional[str] = None


# --- ÖĞÜN PLANI ŞEMALARI (AI önerisi) ---
class MealPlanItemCreate(BaseModel):
    meal_name: str
    time_target: Optional[str] = None
    description: Optional[str] = None
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fats: float = 0.0

class MealPlanItemResponse(MealPlanItemCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# --- GÖRÜNTÜ / FORM ANALİZİ ŞEMALARI ---
class ProgressPhotoConfirmRequest(BaseModel):
    memory_summary: Optional[str] = None


# --- SOHBET ŞEMALARI ---
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    intent: str
    jarvis_reply: str
    data: dict = {}
    enriched: bool = False
    training_advice: Optional[str] = None


# --- PROGRAM OLUŞTURUCU ANKETLERİ (onboarding sonrası detaylı sorular) ---
class WorkoutQuestionnaire(BaseModel):
    """Program Oluşturucu - antrenman anketi. Tüm alanlar opsiyonel; cevaplananlar
    AI prompt'una ek bağlam olarak enjekte edilir ve profile işlenir."""
    environment: Optional[str] = None          # gym | home | outdoor
    equipment: Optional[List[str]] = None      # barbell, dumbbell, machines, cables, ...
    days_per_week: Optional[int] = None
    session_minutes: Optional[int] = None
    preferred_days: Optional[List[str]] = None # Pazartesi, Çarşamba, ...
    preferred_time: Optional[str] = None       # morning | noon | evening | night
    injuries: Optional[str] = None
    avoid_exercises: Optional[str] = None
    training_style: Optional[str] = None       # strength | hypertrophy | hybrid
    focus_muscle_group: Optional[str] = None   # chest | back | legs | shoulders | arms | core | general
    liked_exercises: Optional[str] = None
    disliked_exercises: Optional[str] = None
    cardio_preference: Optional[str] = None    # none | light | moderate | high
    notes: Optional[str] = None


class NutritionQuestionnaire(BaseModel):
    """Program Oluşturucu - beslenme anketi. Tüm alanlar opsiyonel."""
    meals_per_day: Optional[int] = None
    meal_times: Optional[str] = None
    fasting_style: Optional[str] = None        # none | 16_8 | 14_10 | omad
    allergies: Optional[List[str]] = None
    diet_style: Optional[str] = None           # none | vegetarian | vegan | halal | keto | gluten_free
    cooking_skill: Optional[str] = None        # none | basic | good | loves
    meal_prep: Optional[str] = None            # weekly | sometimes | none
    budget: Optional[str] = None               # low | medium | high
    liked_foods: Optional[str] = None
    disliked_foods: Optional[str] = None
    eating_out: Optional[str] = None           # rarely | weekly | often
    supplements: Optional[List[str]] = None
    sleep_hours: Optional[float] = None
    job_activity: Optional[str] = None         # desk | light | physical
    water_intake: Optional[str] = None
    caffeine: Optional[str] = None
    pace: Optional[str] = None                 # aggressive | balanced | slow
    cheat_meal: Optional[str] = None           # none | weekly | biweekly | flexible
    notes: Optional[str] = None
