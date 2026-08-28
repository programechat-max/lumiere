import datetime
import logging
import time

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import settings

logger = logging.getLogger(__name__)

# --- Veritabanı bağlantısı (PROMPT 1: SQLite -> PostgreSQL) ---
# DATABASE_URL ortam değişkeni tanımlıysa (örn. postgresql+psycopg://...) PostgreSQL'e
# bağlanır ve connection pooling devreye girer. Tanımlı değilse geriye dönük uyumluluk
# için yerel SQLite dosyasına düşer (sıfır konfigürasyonla geliştirme deneyimi korunur).
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
IS_SQLITE = SQLALCHEMY_DATABASE_URL.startswith("sqlite")


def _build_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    # PostgreSQL / diğer sunucu tabanlı veritabanları: connection pooling.
    return create_engine(
        url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,  # kopmuş bağlantıları otomatik tespit edip yeniler
    )


def _connect_with_retry(url: str, retries: int = 5, backoff_seconds: float = 1.0):
    """Geçici bağlantı hatalarına karşı üstel geri çekilme (exponential backoff) ile
    bağlantı kurar. Veritabanı henüz ayağa kalkmamışken (örn. docker-compose ile eşzamanlı
    başlatılan Postgres konteyneri) uygulamanın anında çökmesini engeller."""
    engine = _build_engine(url)
    if url.startswith("sqlite"):
        return engine
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except OperationalError as exc:
            last_error = exc
            wait = backoff_seconds * (2 ** (attempt - 1))
            logger.warning("Veritabanına bağlanılamadı (deneme %d/%d), %.1fs sonra tekrar denenecek: %s",
                            attempt, retries, wait, exc)
            time.sleep(wait)
    logger.error("Veritabanına %d denemede bağlanılamadı: %s", retries, last_error)
    return engine  # SQLAlchemy lazy-connect olduğundan engine'i döndürüp asıl hatayı ilk gerçek sorguda yükseltiriz.


engine = _connect_with_retry(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modellerin türeyeceği Base sınıfı
Base = declarative_base()


def migrate_schema():
    """Mevcut veritabanına yeni kolonları güvenli şekilde ekler.
    NOT: Bu, gerçek şema geçmişini/versiyonlamayı yönetmez — üretimde Alembic
    migration'ları (bkz. backend/alembic/) kullanılmalıdır. Bu fonksiyon sadece
    SQLite tabanlı yerel geliştirme + geriye dönük uyumluluk için korunmuştur."""
    import models  # noqa: F401 — tabloları register et

    Base.metadata.create_all(bind=engine)

    if not IS_SQLITE:
        # PostgreSQL/diğer sunucularda şema yönetimi Alembic'e devredilir.
        logger.info("PostgreSQL/harici veritabanı algılandı - kolon bazlı otomatik migrasyon atlanıyor (Alembic kullanın).")
        return

    inspector = inspect(engine)

    # Tabloların varlığını kontrol et
    table_names = inspector.get_table_names()

    # user_memory migration (eskiden beri olan)
    if "user_memory" in table_names:
        existing = {col["name"] for col in inspector.get_columns("user_memory")}
        alters = []
        if "importance" not in existing:
            alters.append("ALTER TABLE user_memory ADD COLUMN importance INTEGER DEFAULT 5")
        if "keywords" not in existing:
            alters.append("ALTER TABLE user_memory ADD COLUMN keywords VARCHAR DEFAULT ''")
        if "memory_key" not in existing:
            alters.append("ALTER TABLE user_memory ADD COLUMN memory_key VARCHAR")
        if "access_count" not in existing:
            alters.append("ALTER TABLE user_memory ADD COLUMN access_count INTEGER DEFAULT 0")
        if "updated_at" not in existing:
            alters.append("ALTER TABLE user_memory ADD COLUMN updated_at DATETIME")
        if alters:
            with engine.begin() as conn:
                for stmt in alters:
                    conn.execute(text(stmt))
            logger.info("user_memory şeması güncellendi (%d kolon)", len(alters))

    # Exercise tablosuna yeni bilimsel kolonları ekle
    if "exercises" in table_names:
        existing = {col["name"] for col in inspector.get_columns("exercises")}
        alters = []
        if "target_rpe" not in existing:
            alters.append("ALTER TABLE exercises ADD COLUMN target_rpe REAL")
        if "exercise_type" not in existing:
            alters.append("ALTER TABLE exercises ADD COLUMN exercise_type VARCHAR")
        if "stretch_mediated" not in existing:
            alters.append("ALTER TABLE exercises ADD COLUMN stretch_mediated BOOLEAN")
        if "unilateral" not in existing:
            alters.append("ALTER TABLE exercises ADD COLUMN unilateral BOOLEAN")
        if "equipment" not in existing:
            alters.append("ALTER TABLE exercises ADD COLUMN equipment VARCHAR")
        if "technique_cue" not in existing:
            alters.append("ALTER TABLE exercises ADD COLUMN technique_cue TEXT")
        if "progression_model" not in existing:
            alters.append("ALTER TABLE exercises ADD COLUMN progression_model VARCHAR")
        if alters:
            with engine.begin() as conn:
                for stmt in alters:
                    conn.execute(text(stmt))
            logger.info("exercises şeması güncellendi (%d kolon)", len(alters))

    # user_profile: kamera/mikrofon izin tercihleri + üyelik planı (PROMPT: üyelik sistemi)
    if "user_profile" in table_names:
        existing = {col["name"] for col in inspector.get_columns("user_profile")}
        alters = []
        if "camera_permission_granted" not in existing:
            alters.append("ALTER TABLE user_profile ADD COLUMN camera_permission_granted BOOLEAN DEFAULT 0")
        if "microphone_permission_granted" not in existing:
            alters.append("ALTER TABLE user_profile ADD COLUMN microphone_permission_granted BOOLEAN DEFAULT 0")
        if "preferred_plan" not in existing:
            alters.append("ALTER TABLE user_profile ADD COLUMN preferred_plan VARCHAR DEFAULT 'FREE'")
        if alters:
            with engine.begin() as conn:
                for stmt in alters:
                    conn.execute(text(stmt))
            logger.info("user_profile şeması güncellendi (%d kolon)", len(alters))

    # Multi-tenancy migration - user_id kolonları ekle
    user_id_tables = [
        "user_profile",
        "workout_programs",
        "workout_logs",
        "nutrition_logs",
        "body_metrics",
        "user_memory",
        "chat_messages",
        "daily_checkins",
        "meal_plan_items"
    ]

    for table_name in user_id_tables:
        if table_name in table_names:
            existing = {col["name"] for col in inspector.get_columns(table_name)}
            if "user_id" not in existing:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER"))
                        # İlk kullanıcıya atayın (eğer kullanıcı varsa)
                        first_user = conn.execute(text("SELECT id FROM users LIMIT 1")).fetchone()
                        if first_user:
                            conn.execute(text(f"UPDATE {table_name} SET user_id = {first_user[0]} WHERE user_id IS NULL"))
                    logger.info(f"{table_name} tablosuna user_id kolonu eklendi")
                except Exception as e:
                    logger.warning(f"{table_name} tablosuna user_id eklenemedi: {e}")

    # Kullanıcı güvenliği (rol/kilitleme) kolonları — PROMPT 2
    if "users" in table_names:
        existing = {col["name"] for col in inspector.get_columns("users")}
        alters = []
        if "role" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'USER'")
        if "failed_login_attempts" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0")
        if "locked_until" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN locked_until DATETIME")
        if "is_email_verified" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT 0")
        if "is_suspended" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN is_suspended BOOLEAN DEFAULT 0")
        if "mfa_secret" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN mfa_secret VARCHAR")
        if "mfa_enabled" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT 0")
        if "deletion_requested_at" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN deletion_requested_at DATETIME")
        if alters:
            with engine.begin() as conn:
                for stmt in alters:
                    conn.execute(text(stmt))
            logger.info("users şeması güncellendi (%d kolon)", len(alters))


def get_db():
    """FastAPI router'ları için veritabanı oturumu sağlar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_date():
    """Bugünün tarihini ISO formatında (YIL-AY-GÜN) döndürür."""
    return datetime.date.today().isoformat()


def get_todays_nutrition_summary(user_id=None):
    """Bugünün toplam kalori ve protein miktarını hesaplayıp döndürür.
    Telegram botunun akşam kontrolü için kullanılır."""
    import models
    from datetime import date
    db = SessionLocal()
    try:
        today = date.today()
        query = db.query(models.NutritionLog).filter(models.NutritionLog.date == today)
        if user_id:
            query = query.filter(models.NutritionLog.user_id == user_id)
        meals = query.all()

        total_cals = sum(m.calories for m in meals if m.calories)
        total_protein = sum(m.protein for m in meals if m.protein)

        return {"calories": total_cals, "protein": total_protein}
    except Exception as e:
        print(f"[VERİTABANI ÖZET HATASI]: {e}")
        return {"calories": 0, "protein": 0}
    finally:
        db.close()


def delete_nutrition_meal(meal_name, user_id=None):
    """Telegram'dan gelen isme göre bugüne ait en son eşleşen öğünü siler."""
    import models
    from datetime import date
    db = SessionLocal()
    try:
        query = (
            db.query(models.NutritionLog)
            .filter(models.NutritionLog.meal_name.like(f"%{meal_name}%"))
            .filter(models.NutritionLog.date == date.today())
        )
        if user_id:
            query = query.filter(models.NutritionLog.user_id == user_id)
        meal = query.order_by(models.NutritionLog.id.desc()).first()

        if meal:
            db.delete(meal)
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"[VERİTABANI SİLME HATASI]: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def edit_nutrition_meal(meal_name, calories, protein, carbs, fats, description=None, user_id=None):
    """Mevcut (bugünkü) bir öğünün makro ve kalori değerlerini günceller."""
    import models
    from datetime import date
    db = SessionLocal()
    try:
        query = (
            db.query(models.NutritionLog)
            .filter(models.NutritionLog.meal_name.like(f"%{meal_name}%"))
            .filter(models.NutritionLog.date == date.today())
        )
        if user_id:
            query = query.filter(models.NutritionLog.user_id == user_id)
        meal = query.order_by(models.NutritionLog.id.desc()).first()

        if meal:
            if calories is not None: meal.calories = float(calories)
            if protein is not None: meal.protein = float(protein)
            if carbs is not None: meal.carbs = float(carbs)
            if fats is not None: meal.fats = float(fats)
            if description is not None: meal.ingredients = description
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"[VERİTABANI GÜNCELLEME HATASI]: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def upsert_nutrition(date_val, meal_name, description, calories, protein, carbs, fats, user_id=None):
    """Telegram'dan gelen makro verilerini veritabanına kaydeder."""
    import models
    db = SessionLocal()
    try:
        new_meal = models.NutritionLog(
            user_id=user_id,
            meal_name=meal_name,
            time_target=datetime.datetime.now().strftime("%H:%M"),
            ingredients=description,
            protein=protein,
            carbs=carbs,
            fats=fats,
            calories=calories,
        )
        db.add(new_meal)
        db.commit()
        return True
    except Exception as e:
        print(f"[VERİTABANI HATASI]: {e}")
        db.rollback()
        return False
    finally:
        db.close()
