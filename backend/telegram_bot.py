import os
import logging
import datetime
import pytz
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, filters, ContextTypes,
)

import ai_core
import crud
import progression
from database import SessionLocal, get_todays_nutrition_summary

load_dotenv()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    logger.critical("[SİSTEM HATASI] .env dosyası eksik! TELEGRAM_BOT_TOKEN ve GEMINI_API_KEY gerekli.")
    exit(1)

# --- ONBOARDING (İLK KURULUM) SOHBET AKIŞI ---
# Kullanıcının hayatına/isteklerine göre kişiselleştirme burada başlıyor.
(ASK_AGE, ASK_HEIGHT, ASK_WEIGHT, ASK_GOAL, ASK_ACTIVITY, ASK_DIET, ASK_SCHEDULE) = range(7)

# --- ANKET (SORU-CEVAP) TARZI PLAN OLUŞTURMA AKIŞI ---
# Beslenme ve antrenman anketleri aynı state makinesini paylaşır (ikisi de aynı yapı:
# N soru sor -> taslak üret -> onay/düzeltme döngüsü).
INTERVIEW_ASKING, INTERVIEW_REVIEW = range(7, 9)


async def profil_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ Profilini oluşturalım efendim. Sana özel program ve beslenme planı için birkaç şey soracağım.\n\n"
        "Yaşın kaç?"
    )
    return ASK_AGE


async def ask_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["age"] = update.message.text
    await update.message.reply_text("Boyun (cm)?")
    return ASK_HEIGHT


async def ask_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["height"] = update.message.text
    await update.message.reply_text("Güncel kilon (kg)?")
    return ASK_WEIGHT


async def ask_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["weight"] = update.message.text
    await update.message.reply_text(
        "Hedefin ne? (örn: kilo almak / yağ yakmak / recomp / formumu korumak) "
        "İstersen hedef fiziğini de tarif et."
    )
    return ASK_GOAL


async def ask_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["goal"] = update.message.text
    await update.message.reply_text(
        "Günlük aktivite/yaşam tarzın nasıl? (masa başı iş mi, hareketli mi, ne sıklıkla antrenman yapıyorsun?)"
    )
    return ASK_ACTIVITY

async def ask_diet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["activity"] = update.message.text
    await update.message.reply_text(
        "Beslenme tercihlerin/kısıtlamaların var mı? (sevmediğin, yiyemediğin, alerjin olan şeyler)"
    )
    return ASK_DIET


async def ask_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["diet"] = update.message.text
    await update.message.reply_text(
        "Son soru: Günlük rutinin nasıl? (uyku saatlerin, iş/okul yoğunluğun, sabah mı akşam mı antrenman yapmayı tercih edersin)"
    )
    return ASK_SCHEDULE


async def finish_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["schedule"] = update.message.text
    ud = context.user_data

    db = SessionLocal()
    try:
        crud.update_profile(db, {
            "age": _safe_int(ud.get("age")),
            "height": _safe_float(ud.get("height")),
            "current_weight": _safe_float(ud.get("weight")),
            "goal": ud.get("goal"),
            "activity_level": ud.get("activity"),
            "dietary_notes": ud.get("diet"),
            "schedule_notes": ud.get("schedule"),
            "onboarding_completed": True,
        })
    finally:
        db.close()

    await update.message.reply_text(
        "✅ Profilin oluşturuldu efendim. Artık seni tanıyorum — bundan sonra yediğin her şeyi, "
        "yaptığın her antrenmanı ve kilonu buraya yazman yeterli, gerisini ben takip edeceğim.\n\n"
        "Şimdi sana özel bir beslenme ve antrenman programı hazırlıyorum, birazdan gelecek. "
        "İstediğin zaman /beslenme veya /antrenman ile yeniden oluşturabilir, /analiz ile "
        "haftalık özet alabilirsin."
    )

    await update.message.reply_text("🍽️ Menü hazırlanıyor...")
    db = SessionLocal()
    try:
        items = ai_core.generate_meal_plan(db)
    finally:
        db.close()
    if items:
        lines = ["📋 [GÜNLÜK BESLENME PROGRAMI]\n"]
        for item in items:
            lines.append(f"🍴 {item.meal_name} ({item.time_target or '-'})\n   {item.description}\n   {item.calories:.0f} kcal | {item.protein:.0f}g protein")
        await update.message.reply_text("\n\n".join(lines))

    await update.message.reply_text("🏋️ Antrenman programı hazırlanıyor...")
    db = SessionLocal()
    try:
        programs = ai_core.generate_workout_program(db)
    finally:
        db.close()
    if programs:
        lines = ["🏋️ [HAFTALIK ANTRENMAN PROGRAMI]\n"]
        for p in programs:
            ex_lines = "\n".join(f"   • {e.name}: {e.target_sets} set x {e.target_reps} tekrar" for e in p.exercises)
            lines.append(f"📅 {p.day_name}\n{ex_lines}")
        await update.message.reply_text("\n\n".join(lines))

    return ConversationHandler.END


async def cancel_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Profil kurulumu iptal edildi. İstediğin zaman /profil ile tekrar başlayabilirsin.")
    return ConversationHandler.END


def _safe_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _safe_float(v):
    try:
        return float(v.replace(",", ".")) if isinstance(v, str) else float(v)
    except (TypeError, ValueError):
        return None


# --- ZAMANLANMIŞ GÖREVLER ---
async def morning_checkin(context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_CHAT_ID:
        text = ("🌅 GÜNAYDIN ŞAMPİYON! Jarvis sistemleri aktif.\n\n"
                "Dün gece uyku kaliten nasıldı ve bu sabah aç karnına kilon kaç? Raporla, göstergeleri güncelleyeyim.")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)


async def evening_macro_check(context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_CHAT_ID:
        return
    try:
        macros = get_todays_nutrition_summary()
        cals = macros.get('calories', 0)
        protein = macros.get('protein', 0)

        db = SessionLocal()
        try:
            profile = crud.get_or_create_profile(db)
            target_cals = profile.daily_calorie_target
        finally:
            db.close()

        if cals < target_cals:
            diff = target_cals - cals
            text = (f"🚨 [SİSTEM UYARISI]: Şampiyon, günü bitirmek üzereyiz ama hedefin gerisindesin!\n\n"
                    f"Şu ana kadar {cals:.0f} kalori ve {protein:.0f}g protein aldın. Hedefe ulaşmak için "
                    f"{diff:.0f} kalori daha alman lazım.")
        else:
            text = (f"✅ [SİSTEM ONAYI]: Hedef tamamlandı! Bugün {cals:.0f} kalori ve {protein:.0f}g protein "
                    f"ile günü kapattın. Şimdi dinlenme vakti.")

        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
    except Exception as e:
        logger.error(f"Zamanlanmış akşam kontrolü hatası: {e}")


async def weekly_auto_analysis(context: ContextTypes.DEFAULT_TYPE):
    """Haftada bir otomatik çalışır - AI son 7 günü analiz edip kullanıcıya rapor atar.
    Bu, uygulamanın 'gelişime yönelik hareket etmesi' isteğini karşılayan kısımdır."""
    if not ADMIN_CHAT_ID:
        return
    analysis = ai_core.generate_weekly_analysis()
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"📊 [HAFTALIK ANALİZ]\n\n{analysis}")


# --- KOMUTLAR ---
async def range_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"⚡ JARVIS AKTİF.\n\n"
        f"Chat ID'n: `{chat_id}` — bunu .env dosyasındaki ADMIN_CHAT_ID kısmına yapıştır.\n\n"
        f"Önce /profil yazarak seni tanımama izin ver, sonra yediklerini/antrenmanlarını "
        f"buraya yazmaya başla. /beslenme ile günlük menü, /antrenman ile haftalık program "
        f"önerisi, /analiz ile haftalık özet, /program ile hareket bazlı ağırlık/tekrar "
        f"önerisi alabilirsin.\n\n"
        f"📸 Bana bir fizik fotoğrafı veya antrenman formu videosu da atabilirsin - "
        f"maksimum hipertrofiye yönelik form/fizik analizi yapıp program ve beslenmeni "
        f"buna göre güncellemeyi önereceğim.\n\n"
        f"🎙️ Yazmak yerine sesli mesaj da atabilirsin - yaptığın antrenmanı, yediğin "
        f"yemeği anlatabilir veya aklına gelen soruyu sorabilirsin, dinleyip cevap veririm.",
        parse_mode='Markdown'
    )


async def manual_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Son 7 günü analiz ediyorum efendim, bir saniye...")
    analysis = ai_core.generate_weekly_analysis()
    await update.message.reply_text(analysis)


async def program_progression(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Her hareket için 'bu antrenmanda ne yapmalıyım' önerisi + genel deload kontrolü."""
    db = SessionLocal()
    try:
        suggestions = progression.get_all_suggestions(db)
        deload = progression.check_deload_needed(db)
    finally:
        db.close()

    if not suggestions:
        await update.message.reply_text(
            "Henüz aktif bir programın yok efendim. Bana hedeflerini anlatırsan senin için bir program yazayım."
        )
        return

    lines = ["🏋️ [PROGRESYON RAPORU]\n"]

    if deload["needs_deload"]:
        deload_reasons = []
        if deload["stagnant_exercises"]:
            deload_reasons.append(f"durağan hareketler: {', '.join(deload['stagnant_exercises'])}")
        if deload["high_fatigue_exercises"]:
            fatigue_str = ", ".join(f"{n} (ort. RPE {r})" for n, r in deload["high_fatigue_exercises"])
            deload_reasons.append(f"yüksek yorgunluk: {fatigue_str}")
        lines.append(
            "⚠️ [DELOAD ÖNERİSİ]: Son antrenmanlarda " + " ve ".join(deload_reasons) + " tespit ettim. "
            "Bu hafta ağırlıkları %40-50 azaltıp aynı tekrarlarla hafif bir toparlanma haftası "
            "geçirmeni öneririm - vücudun tam adapte olsun.\n"
        )

    icons = {"increase_weight": "📈", "hold_weight": "⏸️", "add_reps": "➕", "no_data": "❔", "unknown_range": "❔"}
    for s in suggestions:
        icon = icons.get(s["status"], "•")
        lines.append(f"{icon} {s['exercise_name']}: {s['message']}")

    await update.message.reply_text("\n\n".join(lines))


def _format_meal_plan(items):
    lines = ["📋 [GÜNLÜK BESLENME PROGRAMI - TASLAK]\n"]
    total_cal, total_prot = 0, 0
    for item in items:
        lines.append(f"🍴 {item.meal_name} ({item.time_target or '-'})\n   {item.description}\n   {item.calories:.0f} kcal | {item.protein:.0f}g protein | {item.carbs:.0f}g karb | {item.fats:.0f}g yağ")
        total_cal += item.calories
        total_prot += item.protein
    lines.append(f"\n📊 TOPLAM: {total_cal:.0f} kcal, {total_prot:.0f}g protein")
    return "\n\n".join(lines)


def _format_workout_program(programs):
    lines = ["🏋️ [HAFTALIK ANTRENMAN PROGRAMI - TASLAK]\n"]
    for p in programs:
        ex_lines = "\n".join(f"   • {e.name}: {e.target_sets} set x {e.target_reps} tekrar" for e in p.exercises)
        lines.append(f"📅 {p.day_name}\n{ex_lines}")
    return "\n\n".join(lines)


def _approval_keyboard(kind: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Onayla ve Kaydet", callback_data=f"{kind}_approve")],
        [InlineKeyboardButton("✏️ Değiştir", callback_data=f"{kind}_edit")],
        [InlineKeyboardButton("🔄 Baştan Oluştur", callback_data=f"{kind}_regen")],
    ])


async def generate_nutrition_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının profiline göre günlük öğün TASLAĞI oluşturur ve onay ister -
    kullanıcı onaylamadan veritabanına hiçbir şey yazılmaz."""
    await update.message.reply_text("🍽️ Hedeflerine göre günlük menünü hazırlıyorum efendim, bir saniye...")
    db = SessionLocal()
    try:
        items = ai_core.generate_meal_plan(db, save=False)
    finally:
        db.close()

    if not items:
        await update.message.reply_text(
            "Plan oluşturamadım efendim - önce /profil ile hedeflerini ve tercihlerini anlatır mısın?"
        )
        return

    context.user_data["pending_meal_plan"] = items
    await update.message.reply_text(_format_meal_plan(items), reply_markup=_approval_keyboard("mealplan"))


async def generate_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının profiline göre haftalık antrenman TASLAĞI oluşturur ve onay ister."""
    await update.message.reply_text("🏋️ Hedeflerine göre haftalık programını hazırlıyorum efendim, bir saniye...")
    db = SessionLocal()
    try:
        programs = ai_core.generate_workout_program(db, save=False)
    finally:
        db.close()

    if not programs:
        await update.message.reply_text(
            "Program oluşturamadım efendim - önce /profil ile hedeflerini anlatır mısın?"
        )
        return

    context.user_data["pending_workout_program"] = programs
    await update.message.reply_text(_format_workout_program(programs), reply_markup=_approval_keyboard("workout"))


async def handle_plan_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Onayla/Değiştir/Baştan Oluştur butonlarına basıldığında çalışır."""
    query = update.callback_query
    await query.answer()
    action = query.data  # örn: "mealplan_approve", "workout_edit", "mealplan_regen"

    kind, op = action.rsplit("_", 1)

    if kind == "mealplan":
        pending = context.user_data.get("pending_meal_plan")
        if op == "approve":
            if not pending:
                await query.edit_message_text("Bu taslak artık geçerli değil efendim, /beslenme ile yeniden oluşturur musun?")
                return
            db = SessionLocal()
            try:
                crud.replace_meal_plan(db, pending)
            finally:
                db.close()
            context.user_data.pop("pending_meal_plan", None)
            await query.edit_message_text(_format_meal_plan(pending) + "\n\n✅ Kaydedildi efendim! Dashboard'da da görebilirsin.")
        elif op == "regen":
            await query.edit_message_text("🔄 Yeniden oluşturuluyor...")
            db = SessionLocal()
            try:
                items = ai_core.generate_meal_plan(db, save=False)
            finally:
                db.close()
            context.user_data["pending_meal_plan"] = items
            await query.edit_message_text(_format_meal_plan(items), reply_markup=_approval_keyboard("mealplan"))
        elif op == "edit":
            context.user_data["awaiting_edit"] = "mealplan"
            await query.edit_message_text(
                _format_meal_plan(pending) + "\n\n✏️ Ne değiştirmemi istersin? Yazabilirsin "
                "(örn: 'kahvaltıyı daha az kalorili yap', 'akşam yemeğine balık koy')."
            )

    elif kind == "workout":
        pending = context.user_data.get("pending_workout_program")
        if op == "approve":
            if not pending:
                await query.edit_message_text("Bu taslak artık geçerli değil efendim, /antrenman ile yeniden oluşturur musun?")
                return
            db = SessionLocal()
            try:
                crud.clear_workout_programs(db)
                for ps in pending:
                    crud.create_workout_program(db, ps)
            finally:
                db.close()
            context.user_data.pop("pending_workout_program", None)
            await query.edit_message_text(_format_workout_program(pending) + "\n\n✅ Kaydedildi efendim! Dashboard'da da görebilirsin.")
        elif op == "regen":
            await query.edit_message_text("🔄 Yeniden oluşturuluyor...")
            db = SessionLocal()
            try:
                programs = ai_core.generate_workout_program(db, save=False)
            finally:
                db.close()
            context.user_data["pending_workout_program"] = programs
            await query.edit_message_text(_format_workout_program(programs), reply_markup=_approval_keyboard("workout"))
        elif op == "edit":
            context.user_data["awaiting_edit"] = "workout"
            await query.edit_message_text(
                _format_workout_program(pending) + "\n\n✏️ Ne değiştirmemi istersin? Yazabilirsin "
                "(örn: 'bacak gününe squat ekle', 'pazartesiyi daha hafif yap')."
            )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global hata yakalayıcı. Önceden bu yoktu, bu yüzden herhangi bir kod hatası
    ('No error handlers are registered, logging exception' uyarısıyla) sessizce
    yutuluyordu - kullanıcıya hiç mesaj gitmiyordu, sanki bot cevap vermiyormuş gibi
    görünüyordu. Artık hem tam hata log'a yazılıyor hem kullanıcıya haber veriliyor."""
    logger.error(f"[TELEGRAM HATASI] Güncelleme işlenirken hata: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Sistemlerimde beklenmedik bir hata oluştu efendim, tekrar dener misiniz?",
            )
        except Exception:
            pass


def _physique_action_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏋️ Programı Bu Analize Göre Güncelle", callback_data="physique_apply_training")],
        [InlineKeyboardButton("🍽️ Beslenmeyi Bu Analize Göre Güncelle", callback_data="physique_apply_nutrition")],
        [InlineKeyboardButton("👍 Sadece Not Al, Değiştirme", callback_data="physique_dismiss")],
    ])


async def handle_physique_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı bir fotoğraf ya da video gönderdiğinde çalışır.
    FOTOĞRAF: önce yemek mi fizik/vücut mu olduğunu otomatik ayırt eder (ai_core.analyze_photo).
      - Yemekse: analiz edip doğrudan NutritionLog'a kaydeder (metin ile yemek girmekle aynı UX).
      - Fizikse: hipertrofiye yönelik değerlendirme + program/beslenme güncelleme teklifi sunar.
    VİDEO: her zaman fizik/form analizi olarak işlenir (ai_core.analyze_physique_media)."""
    await update.message.reply_text("🔍 Görüntüyü analiz ediyorum efendim, bu biraz sürebilir...")

    if update.message.photo:
        tg_file = await update.message.photo[-1].get_file()
        mime_type = "image/jpeg"
        is_photo = True
    elif update.message.video:
        tg_file = await update.message.video.get_file()
        mime_type = "video/mp4"
        is_photo = False
    else:
        return

    media_bytes = bytes(await tg_file.download_as_bytearray())
    db = SessionLocal()

    if is_photo:
        try:
            result = ai_core.analyze_photo(media_bytes, mime_type, db)
        finally:
            db.close()

        photo_type = result.get("photo_type")

        if photo_type == "food" and result.get("food"):
            food = result["food"]
            confidence_note = (
                "\n\n⚠️ Porsiyon/malzemeleri net seçemedim, tahmin düşük güvenilirlikte - "
                "yanlışsa yaz, düzelteyim." if food.get("confidence") == "low" else ""
            )
            await update.message.reply_text(
                f"✅ [MATRİS ONAYI]: {food.get('meal_name', 'Öğün')} kaydedildi efendim.\n"
                f"{food.get('description', '')}\n"
                f"{food.get('calories', 0):.0f} kcal | {food.get('protein', 0):.0f}g protein | "
                f"{food.get('carbs', 0):.0f}g karb | {food.get('fats', 0):.0f}g yağ{confidence_note}"
            )
            return

        elif photo_type == "physique" and result.get("physique"):
            physique = result["physique"]
            await update.message.reply_text(physique.get("report", "Analiz tamamlanamadı efendim."))
            training_instr = physique.get("training_instruction")
            nutrition_instr = physique.get("nutrition_instruction")
            if training_instr or nutrition_instr:
                context.user_data["physique_training_instruction"] = training_instr
                context.user_data["physique_nutrition_instruction"] = nutrition_instr
                await update.message.reply_text(
                    "Bu gözlemlere göre bir düzenleme yapmamı ister misin?",
                    reply_markup=_physique_action_keyboard(),
                )
            return

        else:
            await update.message.reply_text(
                result.get("clarify_message") or "Bu fotoğrafın yemek mi yoksa fizik fotoğrafı mı olduğunu anlayamadım efendim, biraz açıklar mısın?"
            )
            return

    # Video her zaman fizik/form analizi
    try:
        result = ai_core.analyze_physique_media(media_bytes, mime_type, db)
    finally:
        db.close()

    await update.message.reply_text(result.get("report", "Analiz tamamlanamadı efendim."))

    training_instr = result.get("training_instruction")
    nutrition_instr = result.get("nutrition_instruction")
    if training_instr or nutrition_instr:
        context.user_data["physique_training_instruction"] = training_instr
        context.user_data["physique_nutrition_instruction"] = nutrition_instr
        await update.message.reply_text(
            "Bu gözlemlere göre bir düzenleme yapmamı ister misin?",
            reply_markup=_physique_action_keyboard(),
        )


async def handle_physique_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fizik analizi sonrası çıkan 'Programı/Beslenmeyi güncelle' butonlarını işler.
    Doğrudan kaydetmez - mevcut taslak+onay akışına (workout/mealplan) girer ki kullanıcı
    yine 'Onayla / Değiştir / Baştan Oluştur' seçeneklerini görsün."""
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "physique_dismiss":
        await query.edit_message_text("👍 Not edildi efendim, program/beslenme aynı kalıyor.")
        return

    if action == "physique_apply_training":
        instruction = context.user_data.get("physique_training_instruction")
        await query.edit_message_text("🏋️ Analize göre program taslağı hazırlanıyor...")
        db = SessionLocal()
        try:
            programs = ai_core.generate_workout_program(db, user_instruction=instruction, save=False)
        finally:
            db.close()
        context.user_data["pending_workout_program"] = programs
        await update.effective_chat.send_message(_format_workout_program(programs), reply_markup=_approval_keyboard("workout"))

    elif action == "physique_apply_nutrition":
        instruction = context.user_data.get("physique_nutrition_instruction")
        await query.edit_message_text("🍽️ Analize göre beslenme taslağı hazırlanıyor...")
        db = SessionLocal()
        try:
            items = ai_core.generate_meal_plan(db, user_instruction=instruction, save=False)
        finally:
            db.close()
        context.user_data["pending_meal_plan"] = items
        await update.effective_chat.send_message(_format_meal_plan(items), reply_markup=_approval_keyboard("mealplan"))


async def process_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    """Serbest metin (veya transkript edilmiş ses) mesajlarını işleyen ORTAK motor.
    Hem handle_message (yazılı) hem handle_voice_message (sesli) burayı çağırır - böylece
    'awaiting_edit' onay akışı ve intent etiketleme mantığı TEK yerde yaşar, ikisi
    arasında tutarsızlık riski olmaz.
    ÖNCELİK: Eğer kullanıcı bir onay kartında 'Değiştir'e basıp düzeltme talimatı yazmayı/
    söylemeyi bekliyorsak (awaiting_edit), bu mesajı normal AI sınıflandırıcısına GÖNDERME -
    direkt o taslağı düzenle."""
    awaiting = context.user_data.get("awaiting_edit")
    if awaiting == "mealplan":
        context.user_data.pop("awaiting_edit", None)
        await update.message.reply_text("🔄 Taslağı güncelliyorum...")
        db = SessionLocal()
        try:
            items = ai_core.generate_meal_plan(db, user_instruction=user_text, save=False,
                                                existing_override=context.user_data.get("pending_meal_plan"))
        finally:
            db.close()
        context.user_data["pending_meal_plan"] = items
        await update.message.reply_text(_format_meal_plan(items), reply_markup=_approval_keyboard("mealplan"))
        return

    if awaiting == "workout":
        context.user_data.pop("awaiting_edit", None)
        await update.message.reply_text("🔄 Taslağı güncelliyorum...")
        db = SessionLocal()
        try:
            programs = ai_core.generate_workout_program(db, user_instruction=user_text, save=False,
                                                          existing_override=context.user_data.get("pending_workout_program"))
        finally:
            db.close()
        context.user_data["pending_workout_program"] = programs
        await update.message.reply_text(_format_workout_program(programs), reply_markup=_approval_keyboard("workout"))
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    result = ai_core.process_message(user_text)
    reply = result.get("jarvis_reply") or "Anladım efendim."

    intent = result.get("intent")
    if intent == "log_workout":
        logged = result.get("_sets_logged", 0)
        failed = result.get("_sets_failed", 0)
        new_prs = result.get("_new_prs", [])
        if logged and not failed:
            tag = f"\n\n💪 [MATRİS ONAYI]: {logged} set kaydedildi."
        elif logged and failed:
            tag = f"\n\n⚠️ [KISMİ ONAY]: {logged} set kaydedildi, {failed} set anlaşılamadı - tekrar yazabilirsin."
        else:
            tag = "\n\n❌ [HATA]: Hiçbir set kaydedilemedi, biraz daha net yazar mısın? (örn: 'bench 3x8 60kg')"

        if new_prs:
            pr_lines = "\n".join(
                f"🏆 {name}: {weight}kg (önceki rekor: {prev}kg)" for name, weight, prev in new_prs
            )
            tag += f"\n\n🎉 [YENİ KİŞİSEL REKOR]!\n{pr_lines}"
    else:
        tag = {
            "log_food": "" if result.get("_food_reply_is_final") else "\n\n✅ [MATRİS ONAYI]: Öğün işlendi.",
            "complete_all_meals": "",
            "log_weight": "\n\n📈 [MATRİS ONAYI]: Ölçüm kaydedildi.",
            "remember": "\n\n🧠 [HAFIZA]: Bunu not ettim, seni daha iyi tanıyorum.",
            "forget": "",
            "modify_meal_plan": "\n\n🔄 [PLAN GÜNCELLENDİ]: Dashboard'da da güncel halini görebilirsin.",
            "delete_meal_plan": "",
            "delete_food_log": "",
            "modify_workout_program": "",
            "delete_workout_program": "",
        }.get(intent, "")

    await update.message.reply_text(reply + tag)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yazılı serbest metin mesajlarını ortak motora (process_user_text) yönlendirir."""
    await process_user_text(update, context, update.message.text)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sesli mesajları (Telegram voice note) Gemini ile Türkçeye transkript edip aynı
    ortak motora (process_user_text) gönderir. Kullanıcı yaptığı antrenmanı, yediği
    yemeği veya aklına gelen bir soruyu konuşarak da girebilir."""
    await update.message.reply_text("🎙️ Ses kaydını dinliyorum efendim...")

    tg_file = await update.message.voice.get_file()
    audio_bytes = bytes(await tg_file.download_as_bytearray())

    transcript = ai_core.transcribe_audio(audio_bytes, mime_type="audio/ogg")

    if not transcript or transcript.strip() == "[ANLAŞILAMADI]":
        await update.message.reply_text(
            "Ses kaydını net anlayamadım efendim, biraz daha yavaş/net tekrar dener misin?"
        )
        return

    await update.message.reply_text(f"📝 Anladığım: \"{transcript}\"")
    await process_user_text(update, context, transcript)




def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    tz = pytz.timezone('Europe/Istanbul')

    app.job_queue.run_daily(morning_checkin, time=datetime.time(hour=8, minute=0, tzinfo=tz))
    app.job_queue.run_daily(evening_macro_check, time=datetime.time(hour=20, minute=0, tzinfo=tz))
    app.job_queue.run_daily(weekly_auto_analysis, time=datetime.time(hour=9, minute=0, tzinfo=tz), days=(0,))  # Pazartesi

    onboarding_handler = ConversationHandler(
        entry_points=[CommandHandler("profil", profil_start)],
        states={
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_height)],
            ASK_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_weight)],
            ASK_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_goal)],
            ASK_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_activity)],
            ASK_ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_diet)],
            ASK_DIET: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_schedule)],
            ASK_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_onboarding)],
        },
        fallbacks=[CommandHandler("iptal", cancel_onboarding)],
    )

    app.add_handler(CommandHandler("start", range_start))
    app.add_handler(onboarding_handler)
    app.add_handler(CommandHandler("analiz", manual_analysis))
    app.add_handler(CommandHandler("program", program_progression))
    app.add_handler(CommandHandler("beslenme", generate_nutrition_plan))
    app.add_handler(CommandHandler("antrenman", generate_program))
    app.add_handler(CallbackQueryHandler(handle_plan_approval, pattern=r"^(mealplan|workout)_"))
    app.add_handler(CallbackQueryHandler(handle_physique_action, pattern=r"^physique_"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_physique_media))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("[JARVIS] Telegram modülü devrede. Dinleniyor...")
    app.run_polling()


if __name__ == '__main__':
    main()
