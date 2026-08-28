import logging
import os
import datetime as dt
from datetime import date

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import settings
from database import engine, Base, get_db, migrate_schema
import models, schemas, crud, auth, ai_core, jarvis_brain, progression
import billing_service
import genai_client

import error_handlers
import middleware as app_middleware
import monitoring
import scheduler as app_scheduler
from rate_limit import enforce_plan_rate_limit
from routes_auth_v1 import router as auth_v1_router
from routes_billing import router as billing_router
from routes_files import router as files_router
from routes_notifications import router as notifications_router
from routes_privacy import router as privacy_router
from routes_jobs import router as jobs_router
from routes_admin import router as admin_router
from routes_support import router as support_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)
migrate_schema()

monitoring.init_sentry()

if settings.ENVIRONMENT == "production" and not settings.COOKIE_SECURE:
    logger.warning("[GUVENLIK] ENVIRONMENT=production ama COOKIE_SECURE=false! Refresh token cookie'si HTTPS olmadan da gönderilecek - .env dosyasında COOKIE_SECURE=true ayarlayın.")

app = FastAPI(title="Jarvis Core Dashboard API", version=settings.APP_VERSION)

# --- Güvenlik & gözlemlenebilirlik middleware zinciri (PROMPT 6/7/8) ---
# NOT: add_middleware çağrı sırası önemlidir - Starlette'te SON eklenen middleware
# EN DIŞTA çalışır. Bu yüzden CORS'u en son ekliyoruz ki 429/500 gibi erken
# dönen yanıtlarda da CORS başlıkları kaybolmasın.
app.add_middleware(app_middleware.IPRateLimitMiddleware)
app.add_middleware(app_middleware.SecurityHeadersMiddleware)
app.add_middleware(app_middleware.RequestContextMiddleware)

# PROMPT 8 (kritik güvenlik açığı): allow_origins=["*"] artık KULLANILMIYOR.
# İzinli origin listesi ALLOWED_ORIGINS ortam değişkeninden okunur (bkz. config.py / .env.example).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

error_handlers.register_error_handlers(app)
monitoring.init_metrics(app)

# --- PROMPT 2/3/4/9/11/12: Yeni v1 API uçları ---
app.include_router(auth_v1_router)
app.include_router(billing_router)
app.include_router(files_router)
app.include_router(notifications_router)
app.include_router(privacy_router)
app.include_router(jobs_router)
app.include_router(admin_router)
app.include_router(support_router)
app.include_router(monitoring.router)


@app.on_event("startup")
def _on_startup():
    app_scheduler.start_scheduler()


@app.on_event("shutdown")
def _on_shutdown():
    app_scheduler.shutdown_scheduler()


@app.get("/health")
def read_root():
    return {"message": "Jarvis API Aktif!"}


# ==========================================
# HESAP / AUTH (kayıt, giriş, mevcut kullanıcı)
# ==========================================
@app.post("/api/auth/register", response_model=schemas.TokenResponse)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = auth.get_user_by_email(db, user_data.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Bu e-posta adresi zaten kullanımda.")

    # Kayıt sırasında seçilen plan doğrulanır; geçersizse güvenli şekilde FREE'e düşer.
    plan = (user_data.preferred_plan or "FREE").upper().strip()
    if plan not in ("FREE", "PRO", "ELITE", "ELITE_PLUS"):
        plan = "FREE"

    new_user = models.User(
        full_name=user_data.full_name,
        email=user_data.email.lower().strip(),
        hashed_password=auth.hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Profili hemen oluştur ve seçilen planı yaz — böylece kullanıcı ilk girişinde
    # plan tercihini kaybolmuş bulmaz.
    profile = crud.get_or_create_profile(db, new_user.id)
    profile.preferred_plan = plan
    db.commit()

    # Üyelik kaydını (Subscription) başlat — Stripe yapılandırılmamış olsa bile
    # plan bilgisi hesapta tutulur ve arayüzden yükseltme/yenileme yapılabilir.
    sub = billing_service.get_or_create_subscription(db, new_user.id)
    sub.plan_type = plan
    db.commit()

    access_token = auth.create_access_token(data={"sub": str(new_user.id)})
    return schemas.TokenResponse(access_token=access_token, user=new_user)


@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı.")

    access_token = auth.create_access_token(data={"sub": str(user.id)})
    return schemas.TokenResponse(access_token=access_token, user=user)


@app.get("/api/auth/me", response_model=schemas.UserResponse)
def read_current_user(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ==========================================
# YAPAY ZEKA DURUMU
# ==========================================
def _require_ai():
    """Gemini API anahtarı yapılandırılmamışsa AI uçlarından anlaşılır bir 503 döner.
    Böylece frontend sessiz 500'ler yerine kullanıcıya ne yapılacağını söyleyebilir."""
    if not genai_client.ai_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Yapay zeka motoru henüz yapılandırılmadı. Sunucudaki backend/.env "
                "dosyasına GEMINI_API_KEY ekleyip backend'i yeniden başlatın "
                "(aistudio.google.com adresinden ücretsiz anahtar alınabilir)."
            ),
        )


# ==========================================
# SİSTEM DURUMU
# ==========================================
@app.get("/api/status")
def get_status(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Frontend'in kilit ekranını açıp açmayacağına karar vermesi için kullanılır.
    Profil onboarding tamamlandıysa VEYA en az bir kayıt varsa kurulum tamamlanmış sayılır.
    NOT: Bilerek get_current_user_optional DEĞİL get_current_user kullanılıyor - bu uç
    sadece giriş yapmış kullanıcının uygulaması tarafından çağrılıyor, token geçersiz/süresi
    dolmuşsa 401 dönüp frontend'in oturumu temizlemesini istiyoruz; sessizce
    'kurulum tamamlanmamış' dönmek kullanıcıyı yanlışlıkla onboarding'e sıkıştırıyordu."""
    profile = crud.get_or_create_profile(db, current_user.id)
    has_any_log = (
        db.query(models.NutritionLog).filter(models.NutritionLog.user_id == current_user.id).first() is not None
        or db.query(models.WorkoutLog).filter(models.WorkoutLog.user_id == current_user.id).first() is not None
    )
    sub = billing_service.get_or_create_subscription(db, current_user.id)
    return {
        "is_setup_complete": bool(profile.onboarding_completed or has_any_log),
        # Frontend, AI destekli özelliklerin (fotoğraftan kalori, form analizi, Jarvis)
        # kullanılabilir olup olmadığını buradan anlar ve kullanıcıyı doğru yönlendirir.
        "ai_configured": genai_client.ai_configured(),
        "plan_type": sub.plan_type or "FREE",
        "plan_status": sub.status or "active",
        # Onboarding'deki açık rıza akışının kalıcı kararı; Ayarlar > İzinler ekranı
        # buradan okur. None => hiç sorulmadı, True/False => kullanıcının kararı.
        "camera_permission_granted": profile.camera_permission_granted,
        "microphone_permission_granted": profile.microphone_permission_granted,
    }


# ==========================================
# PROFİL
# ==========================================
@app.get("/api/profile", response_model=schemas.UserProfileResponse)
def get_profile(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.get_or_create_profile(db, current_user.id)


@app.put("/api/profile", response_model=schemas.UserProfileResponse)
def update_profile(data: schemas.UserProfileBase, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.update_profile(db, data.model_dump(exclude_unset=True), current_user.id)


# ==========================================
# ONBOARDING (vücut videosu + sesli anlatım ile profil oluşturma)
# ==========================================
MAX_UPLOAD_BYTES = 300 * 1024 * 1024  # 300MB - bunun üstü tarayıcıda zaten "Load failed"a yol açar


@app.post("/api/onboarding/video")
async def onboarding_analyze_video(file: UploadFile = File(...), current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db), _rl: bool = Depends(enforce_plan_rate_limit("ai_media"))):
    """Onboarding sırasında iyi ışıkta çekilen VÜCUT VİDEOSUNU analiz eder.
    Aynı Gemini vision motorunu (analyze_physique_media) kullanır: fizik/simetri
    değerlendirmesi yapar, kalıcı hafızaya (UserMemory) özet yazar, varsa somut
    antrenman/beslenme talimatı çıkarır - bunlar sonraki program üretiminde kullanılır."""
    video_bytes = await file.read()
    if not video_bytes:
        raise HTTPException(status_code=400, detail="Boş video dosyası.")
    if len(video_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Video çok büyük (300MB üstü). Kaydı 10-15 saniyeye indirip tekrar dener misin?")
    mime_type = file.content_type or "video/webm"
    logger.info(f"[ONBOARDING] Video alındı: {len(video_bytes) / (1024*1024):.1f}MB, mime={mime_type}")
    _require_ai()

    try:
        os.makedirs("user_videos", exist_ok=True)
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".webm" if "webm" in mime_type else ".mp4"
        with open(os.path.join("user_videos", f"onboarding_{ts}{ext}"), "wb") as f:
            f.write(video_bytes)
    except Exception as e:
        logger.warning(f"Onboarding videosu diske yazılamadı: {e}")

    try:
        return ai_core.analyze_physique_media(video_bytes, mime_type, db, user_id=current_user.id)
    except Exception as e:
        # analyze_physique_media zaten kendi içinde hataları yakalayıp güvenli bir dict
        # döndürüyor; buraya bir şey sızarsa bile bağlantıyı koparmak yerine düzgün bir
        # JSON hata dönelim ki tarayıcıda anlamsız "Load failed" yerine gerçek mesaj görünsün.
        logger.error(f"[ONBOARDING] Video endpoint beklenmeyen hata: {e}")
        raise HTTPException(status_code=500, detail=f"Video işlenirken sunucu hatası: {e}")


@app.post("/api/onboarding/voice")
async def onboarding_analyze_voice(file: UploadFile = File(...), current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db), _rl: bool = Depends(enforce_plan_rate_limit("ai_media"))):
    """Onboarding sırasında kaydedilen SESLİ ANLATIMI (güncel beslenme, antrenman,
    günlük rutin, gerçek hedef) önce metne çevirir (transcribe_audio), sonra bu metni
    yapılandırılmış profil alanlarına ve kalıcı hafızaya dönüştürür
    (extract_profile_from_transcript)."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Boş ses dosyası.")
    if len(audio_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Ses kaydı çok büyük. Daha kısa bir kayıt dener misin?")
    mime_type = file.content_type or "audio/webm"
    logger.info(f"[ONBOARDING] Ses alındı: {len(audio_bytes) / (1024*1024):.1f}MB, mime={mime_type}")
    _require_ai()

    try:
        os.makedirs("user_audio", exist_ok=True)
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".webm" if "webm" in mime_type else ".ogg"
        with open(os.path.join("user_audio", f"onboarding_{ts}{ext}"), "wb") as f:
            f.write(audio_bytes)
    except Exception as e:
        logger.warning(f"Onboarding ses kaydı diske yazılamadı: {e}")

    try:
        transcript = ai_core.transcribe_audio(audio_bytes, mime_type)
        return ai_core.extract_profile_from_transcript(transcript, db, user_id=current_user.id)
    except Exception as e:
        logger.error(f"[ONBOARDING] Ses endpoint beklenmeyen hata: {e}")
        raise HTTPException(status_code=500, detail=f"Ses işlenirken sunucu hatası: {e}")


@app.post("/api/onboarding/complete")
def onboarding_complete(data: schemas.UserProfileBase, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Onboarding'in son adımı. Formdaki temel bilgileri (yaş/boy/kilo/hedef/deneyim vb.)
    profile yazar ve kurulumu tamamlanmış işaretler. Video/ses analizinden biriken
    UserMemory kayıtları + zenginleşmiş profil, build_system_prompt üzerinden otomatik
    olarak devreye girer - bu yüzden burada ekstra talimat geçmeye gerek yok, AI zaten
    kullanıcıyı 'tanıyarak' antrenman programını ve beslenme planını üretir."""
    updates = data.model_dump(exclude_unset=True)
    updates["onboarding_completed"] = True
    profile = crud.update_profile(db, updates, current_user.id)

    # Program üretimi ARTIK burada yapılmıyor: onboarding bittikten sonra
    # 'Program Oluşturucu' anketleri (detaylı sorular) cevaplanır ve üretim
    # /api/program-builder/workout + /api/program-builder/nutrition uçlarından
    # anket cevaplarıyla zenginleştirilmiş bağlamla tetiklenir. Böylece kullanıcı
    # burada 2-4 dk boş beklemez ve programlar çok daha kişiselleşmiş olur.
    return {
        "profile": schemas.UserProfileResponse.model_validate(profile),
        "message": "Profil kaydedildi. Programlar, Program Oluşturucu anketlerinden sonra üretilecek.",
    }


def _persist_questionnaire_to_profile(db: Session, q: dict, user_id: int):
    """Program Oluşturucu anket cevaplarını profilin serbest metin sütunlarına işler.
    Böylece ileride program yeniletiğinde AI bu bağlamı hatırlar (kalıcılık)."""
    profile = crud.get_or_create_profile(db, user_id)
    stamp = "Program Oluşturucu"

    def _join(base: str, add: str) -> str:
        add = (add or "").strip()
        if not add:
            return base
        return f"{base} | {stamp}: {add}" if base else f"{stamp}: {add}"

    if q.get("injuries") or q.get("avoid_exercises"):
        profile.injury_notes = _join(
            profile.injury_notes,
            f"Sakatlık: {q.get('injuries') or 'yok'}; Kaçınılacak hareketler: {q.get('avoid_exercises') or 'yok'}",
        )
    if q.get("preferred_days") or q.get("preferred_time") or q.get("session_minutes"):
        days = ", ".join(q.get("preferred_days") or [])
        profile.schedule_notes = _join(
            profile.schedule_notes,
            f"Antrenman tercihi: {days} {q.get('preferred_time') or ''} {q.get('session_minutes') or ''}dk".strip(),
        )
    if q.get("allergies") or q.get("disliked_foods") or q.get("diet_style") or q.get("liked_foods"):
        profile.dietary_notes = _join(
            profile.dietary_notes,
            f"Alerji: {', '.join(q.get('allergies') or []) or 'yok'}; Diyet stili: {q.get('diet_style') or '-'}; "
            f"Sevmediği: {q.get('disliked_foods') or '-'}; Sevdiği: {q.get('liked_foods') or '-'}",
        )
    if q.get("focus_muscle_group"):
        profile.focus_muscle_group = q["focus_muscle_group"]
    db.commit()
    db.refresh(profile)


@app.post("/api/program-builder/workout")
def program_builder_workout(q: schemas.WorkoutQuestionnaire, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db), _rl: bool = Depends(enforce_plan_rate_limit("ai_workout"))):
    """Program Oluşturucu - ANTRENMAN anketi. Frontend son soruyu cevapladığında
    otomatik çağırır; anket cevapları AI prompt'una ek bağlam olarak enjekte edilir."""
    qd = q.model_dump(exclude_unset=True)
    _persist_questionnaire_to_profile(db, qd, current_user.id)
    try:
        programs = ai_core.generate_workout_program(
            db, user_id=current_user.id, questionnaire=qd, raise_on_error=True
        )
    except Exception as e:
        logger.error(f"[PROGRAM BUILDER] Antrenman üretimi başarısız: {type(e).__name__}: {e!r}")
        raise HTTPException(status_code=502, detail=f"Program oluşturulamadı: {e}")
    return {"workout_programs": programs}


@app.post("/api/program-builder/nutrition")
def program_builder_nutrition(q: schemas.NutritionQuestionnaire, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db), _rl: bool = Depends(enforce_plan_rate_limit("ai_mealplan"))):
    """Program Oluşturucu - BESLENME anketi. Frontend son soruyu cevapladığında
    otomatik çağırır; anket cevapları AI prompt'una ek bağlam olarak enjekte edilir."""
    qd = q.model_dump(exclude_unset=True)
    _persist_questionnaire_to_profile(db, qd, current_user.id)
    try:
        meal_plan_orm = ai_core.generate_meal_plan(
            db, user_id=current_user.id, questionnaire=qd, raise_on_error=True
        )
        meal_plan = [schemas.MealPlanItemResponse.model_validate(item) for item in meal_plan_orm]
    except Exception as e:
        logger.error(f"[PROGRAM BUILDER] Beslenme üretimi başarısız: {type(e).__name__}: {e!r}")
        raise HTTPException(status_code=502, detail=f"Plan oluşturulamadı: {e}")
    return {"meal_plan": meal_plan}



# ==========================================
# BESLENME (frontend /api/nutrition -> bugünün öğün listesi bekliyor)
# ==========================================
@app.get("/api/nutrition")
def get_nutrition_today_list(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Frontend'in beklediği düz liste: [{calories, protein, carbs, ...}, ...]"""
    logs = crud.get_nutrition_logs_by_date(db, date.today(), current_user.id)
    return [
        {
            "id": l.id,
            "meal_name": l.meal_name,
            "ingredients": l.ingredients,
            "calories": l.calories,
            "target_protein": l.protein,
            "target_carbs": l.carbs,
            "target_fat": l.fats,
            "time_target": l.time_target,
        }
        for l in logs
    ]


@app.get("/api/nutrition/today")
def get_today_nutrition(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    logs = crud.get_nutrition_logs_by_date(db, date.today(), current_user.id)
    total_cals = sum(l.calories or 0 for l in logs)
    total_protein = sum(l.protein or 0 for l in logs)
    total_carbs = sum(l.carbs or 0 for l in logs)
    total_fats = sum(l.fats or 0 for l in logs)
    return {
        "date": str(date.today()),
        "summary": {"calories": total_cals, "protein": total_protein, "carbs": total_carbs, "fats": total_fats},
        "meals": logs,
    }


@app.get("/api/nutrition/history")
def get_nutrition_history(days: int = 7, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.get_nutrition_history(db, days=days, user_id=current_user.id)


@app.get("/api/nutrition/day")
def get_nutrition_for_day(day: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Belirli bir güne ait beslenme penceresi. 'day' formatı: YYYY-MM-DD."""
    try:
        target_date = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz tarih formatı, YYYY-MM-DD kullan.")

    logs = crud.get_nutrition_logs_by_date(db, target_date, current_user.id)
    total_cals = sum(l.calories or 0 for l in logs)
    total_protein = sum(l.protein or 0 for l in logs)
    total_carbs = sum(l.carbs or 0 for l in logs)
    total_fats = sum(l.fats or 0 for l in logs)
    return {
        "date": day,
        "summary": {"calories": total_cals, "protein": total_protein, "carbs": total_carbs, "fats": total_fats},
        "meals": logs,
    }


@app.post("/api/nutrition", response_model=schemas.NutritionLogResponse)
def create_nutrition_entry(entry: schemas.NutritionLogCreate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.create_nutrition_log(db, entry, current_user.id)


MAX_PHOTO_BYTES = 15 * 1024 * 1024


@app.post("/api/nutrition/photo")
async def analyze_nutrition_photo(file: UploadFile = File(...), current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Yemek/fizik fotoğrafını analiz eder ama kaydetmez — web arayüzünde kullanıcı
    makroları onayladıktan sonra /api/nutrition/photo/confirm ile kaydedilir."""
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Boş fotoğraf dosyası.")
    if len(image_bytes) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Fotoğraf çok büyük (15MB üstü).")
    mime_type = file.content_type or "image/jpeg"
    _require_ai()
    try:
        return ai_core.analyze_photo(image_bytes, mime_type, db, save=False)
    except Exception as e:
        logger.error(f"[NUTRITION] Fotoğraf analizi hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Fotoğraf analiz edilemedi: {e}")


@app.post("/api/nutrition/photo/confirm", response_model=schemas.NutritionLogResponse)
def confirm_nutrition_photo(entry: schemas.NutritionLogCreate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Web'de fotoğraf analizi sonrası kullanıcının onayladığı öğünü kaydeder."""
    return crud.create_nutrition_log(db, entry, current_user.id)


# ==========================================
# GELİŞİM / FORM FOTOĞRAFI & VİDEOSU ANALİZİ (Akış ekranı "Form Analizi" motoru)
# ==========================================
@app.post("/api/progress/photo")
@app.post("/api/progress/media")
async def analyze_progress_media(file: UploadFile = File(...), current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db), _rl: bool = Depends(enforce_plan_rate_limit("ai_media"))):
    """Kullanıcının vücut/fizik fotoğrafını veya egzersiz form videosunu analiz eder.
    Video veya görsel formatını otomatik tanır ve uygun AI analiz motorunu çalıştırır."""
    media_bytes = await file.read()
    if not media_bytes:
        raise HTTPException(status_code=400, detail="Boş medya dosyası.")
    if len(media_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Dosya çok büyük (300MB üstü).")
    
    mime_type = file.content_type or ("video/mp4" if (file.filename and file.filename.endswith(('.mp4', '.mov', '.webm', '.avi'))) else "image/jpeg")
    is_video = mime_type.startswith("video/") or (file.filename and file.filename.endswith(('.mp4', '.mov', '.webm', '.avi')))
    _require_ai()

    try:
        if is_video:
            res = ai_core.analyze_physique_media(media_bytes, mime_type, db, user_id=current_user.id)
            return {
                "photo_type": "physique",
                "media_type": "video",
                "physique": {
                    "report": res.get("report", ""),
                    "memory_summary": res.get("memory_summary", ""),
                    "training_instruction": res.get("training_instruction"),
                    "nutrition_instruction": res.get("nutrition_instruction"),
                    "form_score": res.get("form_score", 90),
                    "strengths": res.get("strengths", ["Hareket kontrolü", "Ekleme binen yük dengesi"]),
                    "improvements": res.get("improvements", ["Negatif fazda 1 saniye yavaşlama"]),
                },
                "food": None,
                "clarify_message": None,
            }
        else:
            res = ai_core.analyze_photo(media_bytes, mime_type, db, save=False, user_id=current_user.id)
            if res.get("photo_type") == "physique" and res.get("physique"):
                if not res["physique"].get("form_score"):
                    res["physique"]["form_score"] = 88
                if not res["physique"].get("strengths"):
                    res["physique"]["strengths"] = ["Kas simetrisi", "Duruş ve postür stabilitesi"]
                if not res["physique"].get("improvements"):
                    res["physique"]["improvements"] = ["Hedef kas grubunda tepe kasılma odağı"]
            return res
    except Exception as e:
        logger.error(f"[PROGRESS] Form analizi hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Medya analiz edilemedi: {e}")


@app.post("/api/progress/photo/confirm")
def confirm_progress_photo(body: schemas.ProgressPhotoConfirmRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Kullanıcı fizik/form analizi raporunu onayladığında özeti kalıcı hafızaya (UserMemory) yazar."""
    if body.memory_summary:
        crud.create_memory(db, category="physique_analysis", content=body.memory_summary, user_id=current_user.id)
    return {"status": "saved"}


# ==========================================
# JARVIS SOHBET (web arayüzü)
# ==========================================
@app.post("/api/chat", response_model=schemas.ChatResponse)
def chat_with_jarvis(body: schemas.ChatRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db), _rl: bool = Depends(enforce_plan_rate_limit("ai_chat"))):
    """Web dashboard'dan Jarvis ile sohbet — jarvis_brain zeka katmanı ile güçlendirilmiş."""
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Mesaj boş olamaz.")
    session_id = body.session_id or "default"
    result = ai_core.process_message(message, db, session_id=session_id, user_id=current_user.id)
    return schemas.ChatResponse(
        intent=result.get("intent", "chat"),
        jarvis_reply=result.get("jarvis_reply", "Anlayamadım efendim, tekrar dener misiniz?"),
        data=result.get("data") or {},
        enriched=bool(result.get("_enriched")),
        training_advice=result.get("data", {}).get("training_advice"),
    )


@app.get("/api/chat/history")
def get_chat_history(session_id: str = "default", limit: int = 40, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    rows = crud.get_chat_history(db, session_id=session_id, limit=limit, user_id=current_user.id)
    return [
        {"role": r.role, "text": r.content, "intent": r.intent, "created_at": r.created_at.isoformat()}
        for r in rows
    ]


@app.delete("/api/chat/history")
def clear_chat_history(session_id: str = "default", current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    deleted = crud.clear_chat_history(db, session_id=session_id, user_id=current_user.id)
    return {"deleted": deleted}


@app.get("/api/jarvis/briefing")
def get_jarvis_briefing(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Proaktif durum özeti — chat sekmesi açıldığında gösterilir."""
    return jarvis_brain.generate_proactive_briefing(db, current_user.id)


@app.post("/api/jarvis/checkin")
def jarvis_daily_checkin(body: schemas.CheckInRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Yapılandırılmış günlük check-in."""
    result = jarvis_brain.process_checkin(
        db,
        mood=body.mood,
        energy=body.energy,
        sleep_quality=body.sleep_quality,
        soreness=body.soreness,
        notes=body.notes,
        user_id=current_user.id,
    )
    return result


@app.get("/api/memory")
def list_memories(category: str = None, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Jarvis hafıza paneli — tüm kayıtlar."""
    memories = crud.get_all_memories(db, category=category, user_id=current_user.id)
    return [
        schemas.UserMemoryResponse.model_validate(m) for m in memories
    ]


@app.get("/api/memory/search")
def search_memory(q: str, limit: int = 20, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    results = crud.search_memories(db, q, limit=limit, user_id=current_user.id)
    return [schemas.UserMemoryResponse.model_validate(m) for m in results]


@app.put("/api/memory/{memory_id}", response_model=schemas.UserMemoryResponse)
def update_memory(memory_id: int, body: schemas.UserMemoryUpdate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    mem = crud.update_memory(db, memory_id, content=body.content, category=body.category, importance=body.importance, user_id=current_user.id)
    if not mem:
        raise HTTPException(status_code=404, detail="Hafıza kaydı bulunamadı.")
    return mem


@app.delete("/api/memory/{memory_id}")
def delete_memory(memory_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if crud.delete_memory(db, memory_id, user_id=current_user.id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Hafıza kaydı bulunamadı.")


# ==========================================
# GELİŞİM GRAFİKLERİ (birleşik veri)
# ==========================================
@app.get("/api/progress/charts")
def get_progress_charts(days: int = None, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Dashboard gelişim sekmesi için birleşik grafik verisi.
    'days' verilmezse kullanıcının PROGRAMI KULLANMAYA BAŞLADIĞI GÜNDEN (hesap oluşturma
    tarihi) bugüne kadar olan aralık otomatik hesaplanır - grafikler her zaman kullanıcının
    tüm serüvenini gösterir, rastgele sabit bir pencereye (örn. son 14 gün) sıkışmaz."""
    if days is None:
        days = max((date.today() - current_user.created_at.date()).days + 1, 1)

    profile = crud.get_or_create_profile(db, current_user.id)
    metrics = crud.get_body_metrics(db, days=days, user_id=current_user.id)
    nutrition_history = crud.get_nutrition_history(db, days=days, user_id=current_user.id)
    volume = crud.get_weekly_volume_by_muscle_group(db, days=days, user_id=current_user.id)
    meal_plan = crud.get_meal_plan(db, user_id=current_user.id)

    if meal_plan:
        planned_cal = sum(m.calories for m in meal_plan)
        planned_prot = sum(m.protein for m in meal_plan)
    else:
        planned_cal = profile.daily_calorie_target or 2200
        planned_prot = profile.daily_protein_target or 140

    return {
        "weight": [{"date": str(m.date), "weight": m.weight} for m in metrics if m.weight],
        "nutrition": nutrition_history,
        "volume": [{"muscle_group": k, "sets": v} for k, v in sorted(volume.items(), key=lambda x: -x[1])],
        "targets": {
            "calories": planned_cal,
            "protein": planned_prot,
        },
    }


# ==========================================
# BESLENME PLANI (AI önerisi - "ne yemelisin")
# ==========================================
@app.get("/api/mealplan", response_model=list[schemas.MealPlanItemResponse])
def get_meal_plan(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.get_meal_plan(db, user_id=current_user.id)


@app.post("/api/mealplan/generate", response_model=list[schemas.MealPlanItemResponse])
def regenerate_meal_plan(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db), _rl: bool = Depends(enforce_plan_rate_limit("ai_mealplan"))):
    """Dashboard'dan 'Yeni Plan Oluştur' butonuyla tetiklenir."""
    return ai_core.generate_meal_plan(db, user_id=current_user.id)


@app.delete("/api/mealplan")
def delete_meal_plan(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    crud.clear_meal_plan(db, user_id=current_user.id)
    return {"status": "deleted"}


# ==========================================
# ANTRENMAN (frontend /api/workout -> aktif program bekliyor)
# ==========================================
@app.get("/api/workout")
def get_workout(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    programs = crud.get_workout_programs(db, user_id=current_user.id)
    today_logs = crud.get_workout_logs_by_date(db, date.today(), user_id=current_user.id)
    suggestions_by_exercise = {s["exercise_name"].lower(): s for s in progression.get_all_suggestions(db, user_id=current_user.id)}
    return {
        "programs": [
            {
                "id": p.id,
                "day_name": p.day_name,
                "exercises": [
                    {
                        "id": e.id, "name": e.name, "target_sets": e.target_sets, "target_reps": e.target_reps,
                        "progression": suggestions_by_exercise.get(e.name.lower()),
                    }
                    for e in p.exercises
                ],
            }
            for p in programs
        ],
        "today_logs": [
            {"exercise_name": l.exercise_name, "set_number": l.set_number, "weight_lifted": l.weight_lifted, "reps_done": l.reps_done}
            for l in today_logs
        ],
    }


@app.get("/api/workout/day")
def get_workout_for_day(day: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Belirli bir güne ait antrenman penceresi. 'day' formatı: YYYY-MM-DD."""
    try:
        target_date = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz tarih formatı, YYYY-MM-DD kullan.")

    logs = crud.get_workout_logs_by_date(db, target_date, user_id=current_user.id)
    return {
        "date": day,
        "logs": [
            {"exercise_name": l.exercise_name, "set_number": l.set_number, "weight_lifted": l.weight_lifted, "reps_done": l.reps_done, "rpe": l.rpe}
            for l in logs
        ],
        "total_sets": len(logs),
    }


@app.get("/api/workout/progression")
def get_progression_suggestions(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Aktif programdaki her hareket için son antrenmana göre ağırlık/tekrar önerisi.
    Kural tabanlı (deterministik) progressive overload mantığı - AI yorumu değil."""
    return progression.get_all_suggestions(db, user_id=current_user.id)


@app.get("/api/workout/deload")
def get_deload_status(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Son antrenmanlara bakarak deload (hafifletme haftası) gerekip gerekmediğini döndürür."""
    return progression.check_deload_needed(db, user_id=current_user.id)


@app.get("/api/workout/volume")
def get_weekly_volume(days: int = 7, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Kas grubu başına son N gündeki toplam set sayısı - haftalık hacim takibi."""
    return crud.get_weekly_volume_by_muscle_group(db, days=days, user_id=current_user.id)


@app.get("/api/workout/heatmap")
def get_muscle_heatmap(days: int = 7, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Isı haritası için kas grubu başına set + tekrar sayısı."""
    return crud.get_muscle_group_intensity(db, days=days, user_id=current_user.id)


@app.get("/api/workout/heatmap/day")
def get_muscle_heatmap_for_day(day: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Belirli bir GÜNE ait ısı haritası - GÜNLÜK pencerede kullanılır."""
    try:
        target_date = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz tarih formatı, YYYY-MM-DD kullan.")
    return crud.get_muscle_group_intensity_for_date(db, target_date, user_id=current_user.id)


@app.post("/api/workout/program", response_model=schemas.WorkoutProgramResponse)
def create_program(program: schemas.WorkoutProgramCreate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.create_workout_program(db, program, user_id=current_user.id)


@app.post("/api/workout/program/generate")
def generate_program_ai(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db), _rl: bool = Depends(enforce_plan_rate_limit("ai_workout"))):
    """AI'nin profile göre sıfırdan haftalık program oluşturmasını tetikler."""
    # raise_on_error=True: AI hatası sessizce yutulup boş liste dönmesin;
    # hata HTTP 500 + detay olarak frontend'e gitsin ki kullanıcı sorunu görebilsin.
    programs = ai_core.generate_workout_program(db, user_id=current_user.id, raise_on_error=True)
    return crud.get_workout_programs(db, user_id=current_user.id) if programs else []


@app.post("/api/workout/log", response_model=schemas.WorkoutLogResponse)
def log_set(log: schemas.WorkoutLogCreate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.log_workout_set(db, log, user_id=current_user.id)


# ==========================================
# VÜCUT ÖLÇÜMÜ (gelişim takibi)
# ==========================================
@app.post("/api/metrics", response_model=schemas.BodyMetricResponse)
def add_body_metric(data: schemas.BodyMetricCreate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.create_body_metric(db, data, user_id=current_user.id)


@app.get("/api/metrics")
def list_body_metrics(days: int = None, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """'days' verilmezse hesap oluşturma tarihinden bugüne kadar olan aralık kullanılır."""
    if days is None:
        days = max((date.today() - current_user.created_at.date()).days + 1, 1)
    return crud.get_body_metrics(db, days=days, user_id=current_user.id)


# ==========================================
# AI İÇGÖRÜLERİ / HAFTALIK ANALİZ
# ==========================================
@app.get("/api/insights")
def get_insights(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    memories = crud.get_recent_memories(db, limit=15, user_id=current_user.id)
    return [{"id": m.id, "category": m.category, "content": m.content, "created_at": m.created_at} for m in memories]


@app.post("/api/insights/generate")
def trigger_weekly_analysis(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db), _rl: bool = Depends(enforce_plan_rate_limit("ai_insights"))):
    """Dashboard'dan manuel olarak 'Analiz Et' butonuna basınca tetiklenebilir."""
    analysis = ai_core.generate_weekly_analysis(db, user_id=current_user.id)
    return {"analysis": analysis}


# ==========================================
# MARKETING SAYFASI (statik vitrin)
# Bu mount TÜM rotalardan SONRA eklenir: /api/* önce API'ye gider,
# kalan her şey (yani "/") backend/static/index.html'i sunar.
# ==========================================
from fastapi.staticfiles import StaticFiles  # noqa: E402

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="landing")
