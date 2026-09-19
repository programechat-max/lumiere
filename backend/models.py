from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime, Date, JSON, Numeric
from sqlalchemy.orm import relationship
import datetime

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # --- PROMPT 2: Roller / hesap güvenliği ---
    role = Column(String, default="USER", nullable=False, index=True)  # SUPER_ADMIN|ADMIN|SUPPORT|FINANCE|ANALYTICS|COACH|USER
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    is_suspended = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String, nullable=True)
    mfa_enabled = Column(Boolean, default=False, nullable=False)

    # --- PROMPT 11: GDPR hesap silme (30 günlük ödül süreci) ---
    deletion_requested_at = Column(DateTime, nullable=True)


class UserProfile(Base):
    """Kullanıcının kişisel profili, hedefleri ve yaşam tarzı bilgileri.
    Her kullanıcı için ayrı bir profil."""
    __tablename__ = "user_profile"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Fiziksel bilgiler
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)
    current_weight = Column(Float, nullable=True)
    target_weight = Column(Float, nullable=True)

    # Hedef ve deneyim
    goal = Column(String, default="recomp")  # bulk | cut | recomp | maintain
    target_physique = Column(String, default="")
    experience_months = Column(Integer, default=0)
    focus_muscle_group = Column(String, default="")

    # Yaşam tarzı (kişiselleştirme için kritik alanlar)
    activity_level = Column(String, default="moderate")  # sedentary|light|moderate|active
    dietary_notes = Column(Text, default="")   # sevdiği/sevmediği yiyecekler, alerjiler
    schedule_notes = Column(Text, default="")  # uyku/uyanma saatleri, iş/okul yoğunluğu
    injury_notes = Column(Text, default="")    # sakatlık/kısıtlama notları

    # AI tarafından hesaplanan / güncellenen günlük hedefler
    daily_calorie_target = Column(Float, default=2200.0)
    daily_protein_target = Column(Float, default=140.0)
    daily_carb_target = Column(Float, default=220.0)
    daily_fat_target = Column(Float, default=70.0)
    camera_permission_granted = Column(Boolean, default=False)
    microphone_permission_granted = Column(Boolean, default=False)
    preferred_plan = Column(String, default="FREE")

    onboarding_completed = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class WorkoutProgram(Base):
    __tablename__ = "workout_programs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day_name = Column(String, index=True)  # Örn: "Pazartesi - Göğüs & Karın"
    is_active = Column(Boolean, default=True)

    exercises = relationship("Exercise", back_populates="program", cascade="all, delete-orphan")


class Exercise(Base):
    __tablename__ = "exercises"
    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("workout_programs.id"))
    name = Column(String)
    target_sets = Column(Integer)
    target_reps = Column(String)  # Örn: "8-12"
    muscle_group = Column(String, nullable=True)  # Örn: "Göğüs", "Sırt", "Bacak" - hacim takibi için
    target_rpe = Column(Float, nullable=True)
    exercise_type = Column(String, nullable=True)  # primary_compound, secondary_compound, stretch_isolation, shortened_isolation, metabolic, unilateral, core_prehab
    stretch_mediated = Column(Boolean, nullable=True)
    unilateral = Column(Boolean, nullable=True)
    equipment = Column(String, nullable=True)
    technique_cue = Column(Text, nullable=True)
    progression_model = Column(String, nullable=True)

    program = relationship("WorkoutProgram", back_populates="exercises")


class WorkoutLog(Base):
    """Gerçekte yapılan set bazlı antrenman kayıtları."""
    __tablename__ = "workout_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, default=datetime.date.today, index=True)
    exercise_name = Column(String)
    set_number = Column(Integer)
    weight_lifted = Column(Float)
    reps_done = Column(Integer)
    rpe = Column(Integer, nullable=True)  # Zorluk derecesi (1-10)


class NutritionLog(Base):
    """Telegram'dan raporlanan gerçek öğün kayıtları (günlük)."""
    __tablename__ = "nutrition_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, default=datetime.date.today, index=True)
    meal_name = Column(String)
    time_target = Column(String)
    ingredients = Column(Text)
    protein = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    fats = Column(Float, default=0.0)
    calories = Column(Float, default=0.0)

    # --- FAZ 7 (makro/mikro doğrulama katmanı) ---
    # Doğrulama kaynağı: "usda" | "local_db" | "llm_estimate" | None (plan eşleşmesi)
    verification_source = Column(String, nullable=True, index=True)
    verified = Column(Boolean, default=False)
    confidence = Column(String, nullable=True)          # high | medium | low (foto tahminleri)
    # Öğünün mikro kırılımı: {"sodium_mg": x, "potassium_mg": y, "vitamin_c_mg": z, ...}
    micros = Column(JSON, nullable=True)
    # Makro hesaplamanın dayandığı alt kalemler: [{"name","portion_g","calories","protein",
    # "carbs","fats","source","matched_food_id"}] -> Jarvis "şu öğün nereden geldi" şeffaflığı.
    items_breakdown = Column(JSON, nullable=True)


class BodyMetric(Base):
    """Kilo ve vücut ölçümü geçmişi - gelişim takibi için."""
    __tablename__ = "body_metrics"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, default=datetime.date.today, index=True)
    weight = Column(Float, nullable=True)
    waist = Column(Float, nullable=True)
    chest = Column(Float, nullable=True)
    arm = Column(Float, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    note = Column(Text, nullable=True)


class UserMemory(Base):
    """AI'nin kullanıcı hakkında öğrendiği kalıcı bilgiler / haftalık analiz sonuçları.
    Bu tablo Jarvis'in 'kullanıcıyı keşfetmesini' ve zamanla kişiselleşmesini sağlar."""
    __tablename__ = "user_memory"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    category = Column(String, default="note")  # preference | insight | analysis | note | physique_analysis | onboarding_voice
    content = Column(Text)
    importance = Column(Integer, default=5)  # 1-10, yüksek = daha kritik bilgi
    keywords = Column(String, default="")  # virgülle ayrılmış arama anahtar kelimeleri
    memory_key = Column(String, nullable=True, index=True)  # yapılandırılmış anahtar: diet.fish_dislike
    access_count = Column(Integer, default=0)


class ChatMessage(Base):
    """Jarvis web/Telegram sohbet geçmişi — bağlam sürekliliği için."""
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, index=True)  # user | jarvis
    content = Column(Text)
    intent = Column(String, nullable=True)
    session_id = Column(String, default="default", index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class DailyCheckIn(Base):
    """Günlük enerji/uyku/hazırlık check-in — Jarvis proaktif koçluğu için."""
    __tablename__ = "daily_checkins"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, default=datetime.date.today, index=True)
    mood = Column(Integer, nullable=True)  # 1-5
    energy = Column(Integer, nullable=True)  # 1-5
    sleep_quality = Column(Integer, nullable=True)  # 1-5
    soreness = Column(Integer, nullable=True)  # 1-5 (kas ağrısı)
    notes = Column(Text, nullable=True)
    readiness_score = Column(Float, nullable=True)  # 0-100 hesaplanmış hazırlık
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class MealPlanItem(Base):
    """AI tarafından oluşturulan, GÜNÜN önerilen öğün planı.
    NutritionLog'dan farkı: bu 'ne yemelisin' (öneri), NutritionLog ise 'ne yedin' (gerçek kayıt)."""
    __tablename__ = "meal_plan_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    meal_name = Column(String)       # "Kahvaltı", "Öğle Yemeği" vb.
    time_target = Column(String)     # "08:00"
    description = Column(Text)       # önerilen içerik
    calories = Column(Float, default=0.0)
    protein = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    fats = Column(Float, default=0.0)


# ==========================================
# PROMPT 2: OTURUM YÖNETİMİ & AUDIT LOG
# ==========================================
class UserSession(Base):
    """Refresh token oturumları — cihaz/IP takibi, eşzamanlı oturum limiti,
    tekil oturum iptali (logout / 'diğer cihazlardan çıkış yap') için."""
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    refresh_token_hash = Column(String, unique=True, index=True, nullable=False)
    device_name = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    """Tüm kimlik doğrulama + hassas işlemler için değişmez denetim kaydı
    (PROMPT 2 & PROMPT 12 - admin işlemleri de buraya 'admin:' önekiyle yazılır)."""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # işlemin öznesi
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # işlemi yapan (admin impersonation vb.)
    action = Column(String, index=True, nullable=False)  # login_success, login_failed, logout, password_change, admin.suspend_user, ...
    resource = Column(String, nullable=True)
    result = Column(String, default="success")  # success | failure
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


# ==========================================
# PROMPT 3: ABONELİK & FATURALANDIRMA
# ==========================================
class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    plan_type = Column(String, default="FREE", nullable=False)  # FREE|PRO|ELITE|ELITE_PLUS
    status = Column(String, default="active", nullable=False)  # trialing|active|past_due|canceled|unpaid
    trial_end = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    stripe_invoice_id = Column(String, unique=True, index=True, nullable=True)
    amount_due = Column(Numeric(10, 2), default=0)
    currency = Column(String, default="usd")
    status = Column(String, default="open")  # draft|open|paid|uncollectible|void
    pdf_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    stripe_payment_method_id = Column(String, unique=True, index=True, nullable=True)
    brand = Column(String, nullable=True)
    last4 = Column(String, nullable=True)
    exp_month = Column(Integer, nullable=True)
    exp_year = Column(Integer, nullable=True)
    is_default = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class WebhookEvent(Base):
    """İşlenmiş Stripe webhook event id'leri — idempotent işleme için (çift ücretlendirmeyi önler)."""
    __tablename__ = "webhook_events"
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, default="stripe")
    event_id = Column(String, unique=True, index=True, nullable=False)
    event_type = Column(String, nullable=True)
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)


# ==========================================
# PROMPT 4: DOSYA DEPOLAMA (S3)
# ==========================================
class FileAsset(Base):
    __tablename__ = "file_assets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    s3_key = Column(String, nullable=False, unique=True, index=True)
    original_filename = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    category = Column(String, default="general")  # onboarding_video|onboarding_audio|nutrition_photo|general
    processing_status = Column(String, default="pending")  # pending|uploaded|processing|ready|failed
    scan_status = Column(String, default="pending")  # pending|clean|infected|skipped
    error_message = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


# ==========================================
# PROMPT 5: ASENKRON İŞ KUYRUĞU
# ==========================================
class JobStatus(Base):
    __tablename__ = "job_statuses"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    job_type = Column(String, index=True, nullable=False)
    status = Column(String, default="pending")  # pending|started|progress|success|failure
    progress_percent = Column(Integer, default=0)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# ==========================================
# PROMPT 9: iOS PUSH NOTIFICATIONS (APNs)
# ==========================================
class UserDeviceToken(Base):
    __tablename__ = "user_device_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_token = Column(String, unique=True, index=True, nullable=False)
    platform = Column(String, default="ios")
    device_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.datetime.utcnow)


class NotificationSettings(Base):
    __tablename__ = "notification_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    daily_checkin_enabled = Column(Boolean, default=True)
    workout_reminders_enabled = Column(Boolean, default=True)
    weekly_report_enabled = Column(Boolean, default=True)
    inactivity_alerts_enabled = Column(Boolean, default=True)
    billing_alerts_enabled = Column(Boolean, default=True)
    quiet_hours_start = Column(String, default="22:00")
    quiet_hours_end = Column(String, default="08:00")
    timezone = Column(String, default="Europe/Istanbul")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class PushNotificationLog(Base):
    __tablename__ = "push_notification_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_token = Column(String, nullable=True)
    notification_type = Column(String, index=True)  # daily_checkin|workout_reminder|weekly_report|inactivity|billing
    title = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending|sent|failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


# ==========================================
# PROMPT 11: GİZLİLİK / GDPR
# ==========================================
class Consent(Base):
    __tablename__ = "consents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    consent_type = Column(String, index=True)  # data_processing|marketing_emails|analytics
    granted = Column(Boolean, default=False, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    policy_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class DataExportRequest(Base):
    __tablename__ = "data_export_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, default="pending")  # pending|ready|failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class AccountDeletionRequest(Base):
    """30 günlük ödül süreli hesap silme talebi (GDPR right to erasure)."""
    __tablename__ = "account_deletion_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    requested_at = Column(DateTime, default=datetime.datetime.utcnow)
    scheduled_for = Column(DateTime, nullable=False)  # requested_at + 30 gün
    status = Column(String, default="pending")  # pending|canceled|completed
    cancel_token = Column(String, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True)


# ==========================================
# PROMPT 12: ADMİN / DESTEK
# ==========================================
class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    category = Column(String, default="other")  # billing|bug|feature_request|other
    status = Column(String, default="unresolved", index=True)  # unresolved|in_progress|resolved
    assigned_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    messages = relationship("SupportTicketMessage", back_populates="ticket", cascade="all, delete-orphan")


class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_admin_reply = Column(Boolean, default=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    ticket = relationship("SupportTicket", back_populates="messages")


# ==========================================
# BİLGİ KATMANI (KNOWLEDGE LAYER)
# USDA besin verisi, egzersiz kütüphanesi ve bilimsel araştırma notları.
# Bu tablolar KULLANICI BAĞIMSIZ (global) kütüphanelerdir - tüm kullanıcılar
# aynı somut veri havuzunu paylaşır; AI prompt'ları serbest metin uydurmak
# yerine bu tablolardan seçim yapar.
# ==========================================
class FoodItem(Base):
    """Doğrulanmış besin kaydı - 100g başına makrolar + mikro besinler + porsiyon.
    Kaynak: 'usda' (USDA FoodData Central, public domain) | 'local_tr' (Türk
    mutfağı elle kürasyon) | 'ai_added' (USDA'dan canlı çekilip tabloya yazılan
    besin, pending_review=True ile işaretlenir).

    Mikro değerler de 100g başınadır (mg veya µg, sütunda tanımlandığı gibi)."""
    __tablename__ = "food_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)          # kanonik isim: "Tavuk Göğsü (ızgara)"
    aliases = Column(String, default="")                       # virgülle ayrılmış alternatif isimler
    category = Column(String, nullable=True, index=True)       # protein_source | grain | vegetable | fruit | dairy | fat | dish_tr | supplement | other
    calories_per_100g = Column(Float, nullable=False, default=0.0)
    protein_per_100g = Column(Float, nullable=False, default=0.0)
    carbs_per_100g = Column(Float, nullable=False, default=0.0)
    fats_per_100g = Column(Float, nullable=False, default=0.0)
    fiber_per_100g = Column(Float, nullable=True)
    typical_portion_g = Column(Integer, nullable=True)         # örn. 150 (porsiyon gramajı)
    source = Column(String, default="local_tr", index=True)    # usda | local_tr | ai_added
    usda_fdc_id = Column(Integer, nullable=True, index=True)   # USDA FoodData Central FDC ID
    match_score = Column(Float, nullable=True, index=True)    # 0-1: isim/USDA eşleşme güveni
    dietary_tags = Column(String, default="")                  # virgüllü: vegetarian,vegan,gluten_free,lactose_free,high_protein
    pending_review = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # --- MİKRO BESİNLER (100g başına) - USDA FDC nutrient numaralarıyla eşleşir ---
    sodium_mg = Column(Float, nullable=True)          # 1093
    potassium_mg = Column(Float, nullable=True)       # 1092
    calcium_mg = Column(Float, nullable=True)         # 1087
    iron_mg = Column(Float, nullable=True)            # 1089
    magnesium_mg = Column(Float, nullable=True)       # 1090
    zinc_mg = Column(Float, nullable=True)            # 1095
    vitamin_d_ug = Column(Float, nullable=True)       # 1114
    vitamin_b12_ug = Column(Float, nullable=True)     # 1178
    vitamin_c_mg = Column(Float, nullable=True)       # 1162
    # Günlük referans değerler (GDA) -> Jarvis mikro yorumlaması için
    micro_reference = Column(JSON, nullable=True)     # {"sodium_mg": 2000, "potassium_mg": 3500, ...}


class ExerciseLibraryItem(Base):
    """Kanonik egzersiz kütüphanesi kaydı - mevcut Exercise şemasının alanlarıyla
    birebir uyumlu (name, muscle_group, exercise_type, equipment, technique_cue,
    stretch_mediated, unilateral). AI program üretirken hareketleri SADECE bu
    kütüphaneden seçer; kütüphanede gerçekten yoksa pending_review=True ile
    ekleyebilir (kaçış vanası) - sonraki üretimlerde kullanılır."""
    __tablename__ = "exercise_library_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)          # kanonik isim: "Incline Dumbbell Press"
    aliases = Column(String, default="")                       # "Eğimli Dambbell Press, Incline DB Press"
    muscle_group = Column(String, nullable=False, index=True)  # Göğüs | Sırt | Quadriceps | Hamstring & Glute | Omuz | Biceps | Triceps | Karın
    secondary_muscles = Column(String, default="")
    exercise_type = Column(String, nullable=True)              # Exercise.exercise_type ile aynı enum
    stretch_mediated = Column(Boolean, default=False)
    unilateral = Column(Boolean, default=False)
    equipment = Column(String, nullable=True, index=True)      # barbell | dumbbell | cable | machine | bodyweight | kettlebell | band
    technique_cue = Column(Text, nullable=True)
    rep_range_bias = Column(String, nullable=True)             # "6-10" | "8-12" | "10-15" | "12-20"
    contraindications = Column(String, default="")             # sakatlık kısıtları: knee,shoulder,lower_back
    evidence_refs = Column(String, default="")                 # "PMID:12345678,PMID:87654321"
    selection_reason = Column(Text, nullable=True)             # hipertrofi gerekçesi
    pending_review = Column(Boolean, default=False, index=True)
    usage_count = Column(Integer, default=0)                   # programlarda kaç kez seçildi
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # --- FAZ 6 (geniş veri katmanı) kolonları ---
    difficulty = Column(String, default="intermediate", index=True)  # beginner | intermediate | advanced
    force_type = Column(String, nullable=True)                        # push | pull | static | dynamic (split kurarken kullanılır)
    mechanic = Column(String, nullable=True)                          # compound | isolation
    goals = Column(String, default="")                                # hypertrophy|strength|... (hedef filtreleme)
    tags = Column(String, default="")                                 # core_focus|knee_safe|no_axial_load|...
    met = Column(Float, nullable=True)                                # MET değeri -> kalori hesabı
    body_part = Column(String, nullable=True, index=True)             # parquet'ten gelen ham vücut bölgesi
    description = Column(Text, nullable=True)                         # 1-2 cümlelik açıklama
    image_start = Column(String, nullable=True)                       # görsel yolu (başlangıç)
    image_peak = Column(String, nullable=True)                        # görsel yolu (tepe)
    image_main = Column(String, nullable=True)                        # görsel yolu (ana)
    is_bodyweight = Column(Boolean, default=False)
    source = Column(String, default="local_tr", index=True)           # local_tr | parquet_import | usda

    # --- FAZ 7 (kanıta dayalı hipertrofi katmanı) kolonları ---
    # Kasın HANGİ bölümünü (head/region) öncelikli yüklediği - "tüm başları kapsa" kuralının motoru.
    muscle_head = Column(String, nullable=True)         # Kodlanmış: "long_head"|"lateral_head"|"medial_head"|"upper"|"lower"|"clavicular"|"sternal"|...
    # Literatür destekli hipertrofi uyarım puanı (0-10). Küratörlü kayıtlar için elle;
    # parquet kayıtlarında None kalır ve exercise_selector None'ları düşük puanlar.
    stimulus_rating = Column(Float, nullable=True)
    # Hareket açıklığı profili: "full" | "lengthened" | "shortened" | "partial" (izole yükleme kararı)
    rom_profile = Column(String, nullable=True)
    # direct | indirect | mechanistic | expert_curated | unverified
    evidence_level = Column(String, default="unverified", index=True)
    evidence_source = Column(String, nullable=True)
    evidence_scope = Column(String, default="unverified")  # muscle_group | general_mechanistic | direct
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_note = Column(Text, nullable=True)


class ResearchNote(Base):
    """Küratörlü bilimsel bulgu notu (özet + PMID/URL). Program üretiminde
    deterministik, gecikmesiz prompt bağlamı sağlar. PubMed canlı sorgusu
    sadece (yeniden) oluşturmada ve cache'li çalışır - hata halinde bu tablo
    tek başına yeterlidir."""
    __tablename__ = "research_notes"
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False, index=True)         # volume | frequency | stretch | deload | periodization | protein | recovery | prehab
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)                     # 1-3 cümlelik bulgu özeti
    finding_rule = Column(Text, nullable=True)                 # prompt'a giren uygulanabilir kural
    evidence_refs = Column(String, default="")                 # "PMID:12345678" veya URL
    source_type = Column(String, default="curated", index=True)  # curated | pubmed_live
    target_muscle_group = Column(String, nullable=True, index=True)  # null = genel kural
    relevance_score = Column(Integer, default=5)               # 1-10, prompt seçiminde kullanılır
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EvidenceTopic(Base):
    """Küratörlü kanıt konu bankası - Jarvis "Neden X yerine Y?" soruları için.

    Kullanıcı bir hareket seçimi/biyomekanik sorusu sorduğunda önce bu tabloda
    eşleşme aranır (question_keywords + muscle_group); eşleşme varsa direct_answer
    + biomechanics + key_studies (PMID doğrulanmış) Jarvis prompt'una girer ve AI
    küratörlü çekirdeğin üzerine kanıt yapısı kurar. PubMed canlı sorgu bu tabloyu
    tamamlar, asla tek başına çalışmaz (uydurma atıf riskini sıfırlar)."""
    __tablename__ = "evidence_topics"
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False, index=True)        # exercise_choice | biomechanics | nutrition_science | recovery_optimization
    question_keywords = Column(String, default="", index=True)  # virgüllü eşleşme anahtar kelimeleri (TR+EN)
    muscle_group = Column(String, nullable=True, index=True)  # Göğüs | Triceps | ... (null = genel)
    focused_exercises = Column(String, default="")            # virgüllü: "Overhead Cable Extension,Pushdown"
    direct_answer = Column(Text, nullable=False)              # 1-2 cümle net cevap
    biomechanics = Column(Text, nullable=True)                # biyomekanik mekanizma açıklaması
    exercise_recommendations = Column(JSON, nullable=True)    # [{exercise, rep_range, rir, head, why}]
    key_studies = Column(JSON, nullable=True)                 # [{authors, year, title, pmid, journal, link}]
    source_note = Column(Text, nullable=True)                 # sınırlar/uyarılar (insan denemesi verisi vs)
    is_active = Column(Boolean, default=True, index=True)
    priority = Column(Integer, default=5)                     # eşleşmede öncelik sırası
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
