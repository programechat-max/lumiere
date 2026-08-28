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
