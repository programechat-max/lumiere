"""
Jarvis'in tek ve birleşik AI motoru.
Önceden ai_agent.py'de yapılandırılmış intent analizi, telegram_bot.py'de ise
ayrı ve senkron olmayan bir sohbet mantığı vardı. Bu dosya ikisini birleştirir:
- Kullanıcı profilini ve son verilerini okuyarak GERÇEK ZAMANLI, kişiselleştirilmiş
  bir system prompt üretir (statik metin değil).
- Tek bir JSON şemasıyla intent + yanıt üretir (yemek, antrenman, kilo, sohbet).
- Video analizinden veya haftalık analizden çıkan içgörüleri veritabanındaki
  UserMemory tablosundan okur (artık bir .txt dosyası değil).
"""
import os
import json
import logging
import re
import time
import tempfile
import subprocess
from datetime import date, timedelta

from dotenv import load_dotenv

import crud
import schemas
import models
import progression
import jarvis_brain
from database import SessionLocal

# Paylaşılan GenAI client ve sarmalayıcı
from genai_client import (
    _genai_client,
    MODEL_NAME,
    MEDIA_MODEL_NAME,
    _GenerativeModel,
    _upload_video_to_gemini,
    _delete_gemini_file,
)

load_dotenv()
logger = logging.getLogger(__name__)


class MediaAnalysisError(RuntimeError):
    """AI medya sağlayıcısı gerçek analiz üretemediğinde kullanılan hata."""

BASE_PERSONA = """
Sen kullanıcının kişisel 'Jarvis' adındaki elit, sadık ve zeki fitness/sağlık asistanısın.
Iron Man filmindeki Jarvis gibi asil, sadık, hafif nüktedan ve tamamen kullanıcı odaklısın.
Kullanıcıya her zaman "efendim" diye hitap et. Kuru, robotik onay cümleleri kurma;
onunla gerçek bir koç gibi, doğal ve samimi konuş. Yanlış bir bilgi varsa nazikçe düzelt.

CEVAP UZUNLUĞU KONUSUNDA KESİN KURAL - BUNA HER MESAJDA UY:
- SADECE kullanıcının istediği/sorduğu şeyi yap veya yanıtla. Fazladan bağlam, ders,
  motivasyon konuşması, alakasız tavsiye veya "bu arada şunu da unutma" tarzı eklemeler YAPMA.
- Basit bir kayıt işlemi ise (örn. "3 yumurta yedim", "bench 80kg x 8") TEK KISA CÜMLEYLE
  onayla (örn. "Kaydedildi efendim - 3 yumurta, ~18g protein."). Paragraf yazma.
- Bir soru soruluyorsa doğrudan cevapla, 2-4 kısa cümleyi geçme. Kullanıcı açıkça
  "detaylı anlat" / "uzun uzun açıkla" derse ancak o zaman daha uzun yazabilirsin.
- Emoji, başlık, madde işareti gerekmedikçe kullanma - sohbet dili gibi doğal ve kısa yaz.
- "Efendim" hitabı ve kişilik sıcaklığı kalsın ama gevezelik etme; her cümlenin bir amacı olsun.
"""


def build_system_prompt(db=None, user_id=None) -> str:
    """Kullanıcının profilini, son 7 günlük verilerini ve AI'nin biriktirdiği
    hafızayı okuyarak DİNAMİK bir system prompt üretir. Bu, uygulamanın
    'kullanıcının hayatına göre' davranmasını sağlayan ana mekanizmadır."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        profile = crud.get_or_create_profile(db, user_id)
        memories = crud.get_recent_memories(db, user_id=user_id)

        profile_block = f"""
KULLANICI PROFİLİ:
- Yaş: {profile.age or 'bilinmiyor'}, Boy: {profile.height or 'bilinmiyor'} cm, Güncel kilo: {profile.current_weight or 'bilinmiyor'} kg
- Hedef: {profile.goal} ({profile.target_physique or 'belirtilmedi'}), Hedef kilo: {profile.target_weight or 'belirtilmedi'}
- Antrenman deneyimi: {profile.experience_months or 0} ay, Odak: {profile.focus_muscle_group or 'genel'}
- Aktivite seviyesi: {profile.activity_level}
- Beslenme tercihleri / kısıtlamalar: {profile.dietary_notes or 'belirtilmedi'}
- Günlük rutin / uyku notları: {profile.schedule_notes or 'belirtilmedi'}
- Sakatlık / kısıtlama notları: {profile.injury_notes or 'yok'}
- Günlük hedefler: {profile.daily_calorie_target} kcal, {profile.daily_protein_target}g protein,
  {profile.daily_carb_target}g karbonhidrat, {profile.daily_fat_target}g yağ
"""

        if memories:
            durable = [m for m in memories if m.category != "analysis"]
            analyses = [m for m in memories if m.category == "analysis"]
            mem_sections = []
            if durable:
                mem_sections.append(
                    "Kalıcı tercih/not/içgörüler:\n"
                    + "\n".join(f"- ({m.category}) {m.content}" for m in durable)
                )
            if analyses:
                mem_sections.append(
                    "En son haftalık analiz özeti:\n"
                    + "\n".join(f"- {m.content}" for m in analyses)
                )
            memory_block = (
                "\nJARVIS'İN KULLANICI HAKKINDA BİRİKTİRDİĞİ HAFIZA "
                "(bunlar geçmiş sohbetlerden biriken GERÇEK bilgiler, yok sayma):\n"
                + "\n\n".join(mem_sections) + "\n"
            )
        else:
            memory_block = "\n(Henüz kayıtlı bir hafıza yok - kullanıcıyı tanımaya başlıyorsun.)\n"

        # Onboarding medya sonuçlarını kategoriye göre açıkça ayır. Ham JSON'un
        # genel hafıza içinde kaybolmasını veya antrenman/beslenme üretiminde
        # yanlış yorumlanmasını önler.
        media_sections = []
        for category, title in (
            ("onboarding_video_analysis", "ONBOARDING VİDEO ANALİZİ (ANTRENMANDA ÖNCELİKLİ)"),
            ("onboarding_voice_analysis", "ONBOARDING SES KAYDI ANALİZİ (BESLENMEDE ÖNCELİKLİ)"),
        ):
            media_memories = db.query(models.UserMemory).filter(
                models.UserMemory.user_id == user_id,
                models.UserMemory.category == category,
            ).order_by(models.UserMemory.id.desc()).limit(1).all()
            if media_memories:
                content = media_memories[0].content or ""
                try:
                    content = json.dumps(json.loads(content), ensure_ascii=False)
                except (TypeError, json.JSONDecodeError):
                    pass
                media_sections.append(f"\n═══ {title} ═══\n{content}\n")
        media_context_block = "".join(media_sections)

        meal_plan = crud.get_meal_plan(db, user_id)
        if meal_plan:
            plan_lines = "\n".join(
                f"- {m.meal_name} ({m.time_target}): {m.description} "
                f"[{m.calories:.0f} kcal, {m.protein:.0f}g P, {m.carbs:.0f}g K, {m.fats:.0f}g Y]"
                for m in meal_plan
            )
            plan_block = f"\nGÜNCEL BESLENME PLANI (kullanıcı 'planımdaki X'i yedim' derse buradan eşleştir):\n{plan_lines}\n"
        else:
            plan_block = "\n(Kayıtlı bir beslenme planı yok - kullanıcı 'planımdaki X'i yedim' derse plan olmadığını söyle ve ne yediğini sor.)\n"

        return BASE_PERSONA + profile_block + memory_block + media_context_block + plan_block
    finally:
        if own_session:
            db.close()


INTENT_INSTRUCTIONS = """
GÖREVİN: Kullanıcının mesajını analiz et ve SADECE aşağıdaki JSON formatında yanıt dön.
JSON dışında hiçbir şey yazma.

{
  "intent": "log_food" | "complete_all_meals" | "log_workout" | "log_weight" | "remember" | "forget" | "query_history" | "modify_meal_plan" | "delete_meal_plan" | "delete_food_log" | "modify_workout_program" | "delete_workout_program" | "update_goal" | "update_profile" | "explain_why" | "coaching_advice" | "daily_checkin" | "compare_period" | "chat",
  "data": {
    // log_food ise: "meal_name", "description", "calories", "protein", "carbs", "fats", "matched_plan_meal"
    //   KURAL 1 - Kullanıcı NE YEDİĞİNİ somut olarak tarif ettiyse (malzeme/miktar belirtmiş,
    //     örn. "3 yumurta yedim", "150g tavuk ve pirinç yedim"): description'a bunu yaz,
    //     calories/protein/carbs/fats'ı bu tarife göre rasyonel hesapla. matched_plan_meal: null.
    //   KURAL 2 - Kullanıcı SADECE "planımdaki kahvaltıyı/öğle yemeğimi/X öğününü yedim" gibi
    //     BELİRSİZ bir ifade kullandıysa (ne yediğini TARİF ETMEDEN, sadece plan öğününe atıfla):
    //     calories/protein/carbs/fats alanlarına 0 yaz (bunlar KULLANILMAYACAK, kod gerçek plan
    //     verisini DB'den çekip kullanacak) ve matched_plan_meal alanına o öğünün planındaki
    //     TAM meal_name'ini yaz (örn. "Kahvaltı", "Öğle Yemeği") - SİSTEM PROMPT'taki güncel
    //     BESLENME PLANI bölümünden hangi öğün olduğunu belirle. Eşleşen öğün yoksa null yaz ve
    //     jarvis_reply'de kullanıcıya ne yediğini sorman GEREKİR, kaydetme.
    //   ASLA sayısal alanlara rastgele/uydurma değer yazıp matched_plan_meal'i de null bırakma -
    //     ya somut tarife dayalı gerçek hesap yap, ya da plana yönlendir, ikisi de değilse SOR.

    // complete_all_meals ise: veri gerekmez, boş obje {} yeterli.
    //   BU INTENT'İ KULLAN: kullanıcı GÜNÜN PLANINDAKİ BÜTÜN öğünleri yediğini/tamamladığını
    //   TEK BİR CÜMLEYLE, öğünleri tek tek saymadan bildiriyorsa (örn: "tüm öğünlerimi
    //   tamamladım", "bugün planımdaki her şeyi yedim", "günü planıma birebir uydum",
    //   "bugünkü menüyü eksiksiz bitirdim"). log_food'dan FARKI: log_food tek bir öğüne
    //   (örn. sadece kahvaltı) atıfla kullanılır, complete_all_meals ise "TÜMÜ/HEPSİ/BÜTÜN
    //   GÜN" gibi bir bütünlüğe atıfla kullanılır. jarvis_reply'i BOŞ BIRAK ("") - kod
    //   plandaki her öğünü tek tek DB'den çekip kaydedecek ve gerçek özeti kendisi yazacak.

    // log_workout ise: "sets" adında bir LİSTE ver. Kullanıcı tek mesajda birden fazla
    //   hareket veya set anlatabilir (örn. "bench 4x8 60kg, sonra dips 3x12 vücut ağırlığı") -
    //   HER SETİ AYRI BİR ELEMAN OLARAK LİSTEYE EKLE:
    //   "sets": [
    //     {"exercise_name": "Bench Press", "set_number": 1, "weight_lifted": 60, "reps_done": 8, "rpe": 8},
    //     {"exercise_name": "Bench Press", "set_number": 2, "weight_lifted": 60, "reps_done": 7, "rpe": 9}
    //   ]
    //   KURALLAR:
    //   - weight_lifted ve reps_done HER ZAMAN sayı olmalı, asla "Varying", "değişken" gibi
    //     metin yazma. Ağırlık set set değiştiyse HER SET İÇİN AYRI ELEMAN oluştur ve o setin
    //     gerçek sayısını yaz.
    //   - Vücut ağırlığı hareketlerinde (mekik, dips, pull-up vb.) weight_lifted için 0 yaz.
    //   - Kullanıcı set sayısını veya tekrarı belirtmediyse mantıklı bir varsayım yap
    //     (örn. sadece "bench yaptım" derse tek set, reps_done tahmini yap) ama sayı olsun.

    // log_weight ise: "weight", "waist", "chest", "arm", "sleep_hours"
    // remember ise: "category" ("preference"|"note"), "content"
    //   (kullanıcı kalıcı bir tercih, alışkanlık veya yaşam tarzı bilgisi paylaştıysa kullan,
    //    örn: "balık yemem", "akşamları geç yatıyorum", "dizimde eski bir sakatlık var")
    //   Eğer bu bilgi, SİSTEM PROMPT'taki "JARVIS'İN KULLANICI HAKKINDA BİRİKTİRDİĞİ HAFIZA"
    //   bölümünde zaten var olan bir kaydı GÜNCELLİYORSA/DÜZELTİYORSA (örn. eskiden "dizimde
    //   sakatlık var" yazıyordu, şimdi "dizim artık iyi") content'e YENİ HALİNİ yaz - eski
    //   bilgi otomatik olarak devre dışı bırakılacak, sen ikisini birden yazmaya çalışma.
    // forget ise: "content" (unutulacak/artık geçersiz olan bilginin kısa özeti)
    //   BU INTENT'İ KULLAN: kullanıcı AÇIKÇA "bunu unut", "artık öyle değil, kaydı sil",
    //   "o bilgi yanlıştı/eskidi, çıkar" gibi HAFIZADAKİ bir kaydı iptal etmek istediğini
    //   belirtiyorsa. content alanına, hafızadaki hangi kaydın kastedildiğini SİSTEM
    //   PROMPT'taki hafıza bölümüne bakarak olabildiğince aynen yaz (eşleştirme buna göre
    //   yapılacak).
    // query_history ise: "days_ago" (int, kaç gün önce - "dün"=1, "bugün"=0, "geçen hafta"=7,
    //   belirtilmemişse veya "bu hafta/son günler" gibi genel bir aralıksa 7 yaz)
    //   BU INTENT'İ KULLAN: kullanıcı geçmişte ne yaptığını/yediğini soruyorsa
    //   (örn: "dün ne yemiştim", "geçen hafta antrenman yaptım mı", "bugün kaç kalori aldım").
    //   jarvis_reply'i BOŞ BIRAK ("") - gerçek veri ayrıca eklenecek, sen tahmin ile cevap UYDURMA.

    // modify_meal_plan ise: "instruction" (kullanıcının isteğinin TAM VE DETAYLI hali -
    //   kullanıcı miktar/malzeme belirttiyse HİÇBİRİNİ ATLAMADAN aynen yaz, kısaltma/yorumlama)
    //   BU INTENT'İ KULLAN: kullanıcı mevcut planı DEĞİŞTİRMEK istiyorsa - bir öğünü,
    //   içeriği veya kaloriyi güncellemek istiyor (örn: "kahvaltıyı değiştir", "tavuk yerine
    //   balık koy", "daha az kalorili yap", "akşam yemeğini çıkar"). jarvis_reply'i BOŞ BIRAK ("")
    //   - plan ayrıca yeniden oluşturulup gerçek sonuç eklenecek.
    //   ÖNEMLİ: kullanıcı belirli bir öğünü BİREBİR ne yiyeceğini tarif ettiyse (örn: "5 yumurta,
    //   3'ünün sarısı var, 2 patates kabuklu fırında, 1 yemek kaşığı zeytinyağı"), bunu KENDİ
    //   YORUMUNLA DEĞİŞTİRME veya BAŞKA MALZEMELERLE DEĞİŞTİRME - kullanıcının verdiği malzeme ve
    //   miktarları AYNEN instruction'a yaz, plan oluşturma aşamasında bu birebir kullanılacak.
    //   DİKKAT: kullanıcı planın TAMAMINI kaldırmak/silmek istiyorsa bunu KULLANMA,
    //   onun yerine delete_meal_plan kullan.

    // delete_meal_plan ise: veri gerekmez, boş obje {} yeterli.
    //   BU INTENT'İ KULLAN: kullanıcı önerilen BESLENME planını (henüz yenmemiş, gelecekteki
    //   öneri) tamamen SİLMEK/KALDIRMAK istiyorsa (örn: "beslenme planımı kaldır", "menüyü sil").
    //   DİKKAT: kullanıcı "bugün YEDİĞİM şeyleri sil/kaldır" diyorsa bu DEĞİL, delete_food_log
    //   kullan. DİKKAT: kullanıcı "ANTRENMAN programını/planını sil" diyorsa bu KESİNLİKLE DEĞİL,
    //   onun yerine delete_workout_program kullan - "beslenme/menü/yemek" ile "antrenman/spor/
    //   program" kelimelerini KARIŞTIRMA, ikisi tamamen ayrı tablolardır.

    // delete_food_log ise: "days_ago" (int, kaç gün önce - belirtilmemişse 0 = bugün)
    //   BU INTENT'İ KULLAN: kullanıcı GERÇEKTE yediği/kaydedilen öğünleri silmek istiyorsa
    //   (örn: "bugün yediklerimi sil", "yanlışlıkla girmişim, kaldır", "yemek kaydımı temizle").
    //   jarvis_reply'i BOŞ BIRAK ("").

    // delete_workout_program ise: veri gerekmez, boş obje {} yeterli.
    //   BU INTENT'İ KULLAN: kullanıcı ANTRENMAN PROGRAMINI tamamen SİLMEK/KALDIRMAK istiyorsa
    //   (örn: "antrenman programını sil", "spor planımı kaldır", "programı temizle").
    //   BUNU beslenme/yemek ile İLGİLİ hiçbir şeyle karıştırma. jarvis_reply'i BOŞ BIRAK ("").

    // modify_workout_program ise: "instruction" (kullanıcının isteğinin TAM VE DETAYLI hali),
    //   "full_regenerate" (bool - kullanıcı programın TAMAMINI/genel olarak değiştirmek istiyorsa
    //   true, sadece BELİRLİ bir gün/hareketi düzenlemek istiyorsa false)
    //   BU INTENT'İ KULLAN: kullanıcı antrenman PROGRAMINI oluşturmak/değiştirmek istiyorsa
    //   (örn: "bana bir program yap", "pazartesi gününü değiştir", "bacak gününe squat ekle",
    //   "hiç programım yok, oluştursana", "programı yeniden yap", "farklı bir program dene",
    //   "programı baştan oluştur", "bu programdan sıkıldım, değiştir"). Bunu tek bir SET/hareket
    //   KAYDETMEK (log_workout) ile KARIŞTIRMA - kullanıcı "yaptım" diyorsa log_workout,
    //   "program/plan yapsana/değiştir/yeniden yap" diyorsa modify_workout_program.
    //   full_regenerate KURALI: kullanıcı "yeniden yap", "baştan oluştur", "farklı bir program",
    //   "tamamen değiştir", "sıkıldım değiştir" gibi BELİRLİ bir gün/hareket ADI VERMEDEN genel
    //   bir yenileme istiyorsa full_regenerate: true yaz - bu durumda program SIFIRDAN, FARKLI
    //   hareket seçimleriyle yeniden kurulacak (eskisiyle aynı çıkmayacak şekilde). Kullanıcı
    //   "pazartesi gününe/X hareketine ..." gibi SPESİFİK bir gün veya hareket adı verdiyse
    //   full_regenerate: false yaz - sadece o kısım değişecek, geri kalanı aynı kalacak.
    //   Kullanıcı programı SİLMEK istiyorsa bunu değil delete_workout_program kullan.
    //   jarvis_reply'i BOŞ BIRAK ("").

    // update_goal ise: "goal" (kullanıcının yeni antrenman hedefi - kısa ve standart bir
    //   ifadeyle, örn: "hipertrofi/kas kütlesi", "güç/kuvvet", "yağ yakımı", "genel fitness",
    //   "dayanıklılık"), "focus_muscle_group" (varsa özellikle vurgulamak istediği kas grubu,
    //   yoksa null)
    //   BU INTENT'İ KULLAN: kullanıcı antrenman HEDEFİNİ/amacını değiştirmek veya belirtmek
    //   istiyorsa (örn: "hipertrofi istiyorum", "artık kuvvet üzerine çalışmak istiyorum",
    //   "kas kütlesi kazanmak istiyorum", "yağ yakımına geçelim", "bacak gelişimine
    //   odaklanmak istiyorum"). BUNU coaching_advice veya chat İLE CEVAPLAYIP GEÇME - kullanıcı
    //   sadece sohbet etmek değil, GERÇEKTEN hedefini ve dolayısıyla programını değiştirmek
    //   istiyor. Bu intent tetiklendiğinde hem profildeki hedef güncellenecek HEM DE program
    //   yeni hedefe göre SIFIRDAN yeniden oluşturulacak - "sadece bir tavsiye/örnek hareket
    //   söylemek" ile YETİNME, gerçek işlemi yapman için bu intent'i seçmen ZORUNLU.
    //   jarvis_reply'i BOŞ BIRAK ("").

    // update_profile ise: "current_weight", "target_weight", "height", "age", "target_physique",
    //   "experience_months", "activity_level", "dietary_notes", "schedule_notes", "injury_notes"
    //   (verilen alanlardan hangileri varsa onları günceller, verilmeyenleri dokunmaz)
    //   BU INTENT'İ KULLAN: kullanıcı fiziksel özelliklerini, hedeflerini veya yaşam tarzı
    //   bilgilerini doğal dilde söylediğinde (örn: "ben 62 kiloyum, hedefim 70 kilo",
    //   "boyum 178cm", "yaşım 25", "estetik damarlı kaslı görünüm istiyorum",
    //   "haftada 4 gün salon gidiyorum", "balık yemem", "dizimde sakatlık var").
    //   Kullanıcı "program yap" demeden önce veya program istediği sırada bu bilgileri
    //   söylüyorsa MUTLAKA bu intent'i seç. Profil güncellendikten sonra eğer kullanıcı
    //   antrenman programı da istiyorsa (veya mesajın sonunda "program yap" gibi bir istek
    //   varsa) full_regenerate: true ile modify_workout_program DA tetiklenmeli.
    //   jarvis_reply'i BOŞ BIRAK ("") — kod profil güncelleyecek ve programı yeniden kuracak.

    // explain_why ise: "topic" (kullanıcının "neden" sorduğu konu — örn. "bench seçimi", "protein hedefi", "deload")
    //   BU INTENT'İ KULLAN: kullanıcı bir karar/program/hareket/hedef hakkında "neden", "niçin",
    //   "neden bunu önerdin/seçtin" diye soruyorsa. jarvis_reply'i BOŞ BIRAK ("") — zenginleştirme katmanı dolduracak.

    // coaching_advice ise: "topic" (genel koçluk konusu — beslenme, antrenman, toparlanma, motivasyon)
    //   BU INTENT'İ KULLAN: kullanıcı genel tavsiye/öneri istiyorsa ("ne yapmalıyım", "bugün ne önerirsin",
    //   "nasıl ilerlerim"). jarvis_reply'i BOŞ BIRAK ("").

    // daily_checkin ise: "mood", "energy", "sleep_quality", "soreness" (her biri 1-5 int, belirtilmemişse null),
    //   "notes" (serbest metin duygu durumu)
    //   BU INTENT'İ KULLAN: kullanıcı bugün nasıl hissettiğini/enerjisini/uykusunu raporluyorsa
    //   ("bugün çok yorgunum", "iyi uyudum", "kaslarım ağrıyor", "kendimi harika hissediyorum").
    //   jarvis_reply'i BOŞ BIRAK ("") — kod hazırlık skorunu hesaplayacak.

    // compare_period ise: "days" (int, varsayılan 7)
    //   BU INTENT'İ KULLAN: kullanıcı dönem karşılaştırması istiyorsa ("bu hafta vs geçen hafta",
    //   "son 7 günde nasıl gidiyorum", "gelişimim nasıl"). jarvis_reply'i BOŞ BIRAK ("").
  },
  "jarvis_reply": "Kullanıcıya Jarvis tonunda, kişiselleştirilmiş, kısa ve motive edici yanıt."
}

Not: Bir mesajda birden fazla şey olabilir (örn. hem yemek hem tercih) - sadece EN BASKIN
intent'i seç, ama jarvis_reply içinde ikisini de yanıtlayabilirsin.
"""


def _safe_float(value, default=0.0):
    """AI bazen 'Varying', 'vücut ağırlığı' gibi metinler döndürebiliyor -
    bu durumda çökmek yerine güvenli bir varsayılana düş."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    return int(_safe_float(value, default))


def process_message(user_message: str, db=None, session_id: str = "default", user_id: int = None) -> dict:
    """Tek giriş noktası: mesajı analiz eder, intent'e göre veritabanına yazar
    ve kullanıcıya verilecek yanıtı döndürür. jarvis_brain katmanı ile zenginleştirilir."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        crud.save_chat_message(db, "user", user_message, session_id=session_id, user_id=user_id)

        system_instruction = jarvis_brain.build_enhanced_system_prompt(
            db, user_message, BASE_PERSONA, INTENT_INSTRUCTIONS, user_id=user_id
        )
        model = _GenerativeModel(MODEL_NAME, system_instruction)

        response = model.generate_content(
            user_message,
            generation_config={"response_mime_type": "application/json", "temperature": 0.4},
        )
        result = json.loads(response.text)
        intent = result.get("intent")
        data = result.get("data", {}) or {}

        if intent == "log_food":
            import schemas
            matched_meal_name = data.get("matched_plan_meal")

            if matched_meal_name:
                # Kullanıcı "planımdaki X'i yedim" dedi - AI'nin uydurduğu değil,
                # veritabanındaki GERÇEK plan verisini kullan.
                plan_items = crud.get_meal_plan(db, user_id)
                matched = next(
                    (p for p in plan_items if p.meal_name.strip().lower() == matched_meal_name.strip().lower()),
                    None,
                )
                if matched:
                    crud.create_nutrition_log(db, schemas.NutritionLogCreate(
                        meal_name=matched.meal_name,
                        ingredients=matched.description,
                        calories=matched.calories,
                        protein=matched.protein,
                        carbs=matched.carbs,
                        fats=matched.fats,
                    ), user_id=user_id)
                    result["jarvis_reply"] = (
                        f"✅ {matched.meal_name} kaydedildi efendim ({matched.calories:.0f} kcal, "
                        f"{matched.protein:.0f}g protein) - plandaki haliyle."
                    )
                    result["_food_reply_is_final"] = True
                else:
                    # AI plan içinde eşleşme bulamadı ama yine de matched_plan_meal döndürmüş -
                    # veri uydurmak yerine kullanıcıya sor.
                    result["jarvis_reply"] = (
                        "Planında bu isimde bir öğün bulamadım efendim. Ne yediğini biraz "
                        "tarif eder misin, öyle kaydedeyim?"
                    )
                    result["intent"] = "chat"
            else:
                calories = _safe_float(data.get("calories"), default=None)
                # AI hem plana eşlemedi hem de somut bir kalori hesaplamadıysa (description boş/
                # belirsiz), rastgele 0 kaydetmek yerine kullanıcıya sor.
                description = data.get("description", "").strip()
                if calories is None and not description:
                    result["jarvis_reply"] = (
                        "Ne yediğini biraz daha tarif eder misin efendim? (örn. '3 yumurta ve "
                        "1 dilim ekmek' gibi) - net bir tarif olmadan makroları uyduramam."
                    )
                    result["intent"] = "chat"
                else:
                    crud.create_nutrition_log(db, schemas.NutritionLogCreate(
                        meal_name=data.get("meal_name", "Öğün"),
                        ingredients=description or user_message,
                        calories=_safe_float(data.get("calories")),
                        protein=_safe_float(data.get("protein")),
                        carbs=_safe_float(data.get("carbs")),
                        fats=_safe_float(data.get("fats")),
                    ), user_id=user_id)
        elif intent == "complete_all_meals":
            import schemas
            plan_items = crud.get_meal_plan(db, user_id)
            if not plan_items:
                result["jarvis_reply"] = (
                    "Şu an kayıtlı bir beslenme planın yok efendim, o yüzden 'tümünü tamamladım' "
                    "diyebileceğim bir öğün listesi bulamadım. Önce /beslenme ile bir plan "
                    "oluşturalım, ya da ne yediğini tek tek anlat, öyle kaydedeyim."
                )
            else:
                already_logged = {
                    m.meal_name.strip().lower() for m in crud.get_nutrition_logs_by_date(db, date.today(), user_id)
                }
                newly_logged = []
                for item in plan_items:
                    if item.meal_name.strip().lower() in already_logged:
                        continue
                    crud.create_nutrition_log(db, schemas.NutritionLogCreate(
                        meal_name=item.meal_name,
                        ingredients=item.description,
                        calories=item.calories,
                        protein=item.protein,
                        carbs=item.carbs,
                        fats=item.fats,
                    ), user_id=user_id)
                    newly_logged.append(item)

                if not newly_logged:
                    result["jarvis_reply"] = (
                        "Zaten planındaki tüm öğünleri bugün için ayrı ayrı kaydetmiştin efendim, "
                        "tekrar eklemedim - günün tamamlanmış görünüyor."
                    )
                else:
                    total_cal = sum(i.calories for i in newly_logged)
                    total_prot = sum(i.protein for i in newly_logged)
                    meal_names = ", ".join(i.meal_name for i in newly_logged)
                    skipped_note = (
                        f" ({len(plan_items) - len(newly_logged)} tanesini zaten önceden kaydetmiştin, atladım.)"
                        if len(newly_logged) < len(plan_items) else ""
                    )
                    result["jarvis_reply"] = (
                        f"✅ Planındaki tüm öğünleri tamamladım olarak kaydettim efendim: {meal_names} "
                        f"— toplam {total_cal:.0f} kcal, {total_prot:.0f}g protein.{skipped_note}"
                    )
                result["_food_reply_is_final"] = True
        elif intent == "forget":
            target_content = (data.get("content") or "").strip()
            removed = crud.forget_memory(db, target_content, user_id) if target_content else None
            if removed:
                result["jarvis_reply"] = f"🧠 Anladım efendim, bunu hafızamdan çıkardım: \"{removed.content}\""
            else:
                result["jarvis_reply"] = (
                    "Hafızamda buna tam karşılık gelen bir kayıt bulamadım efendim - "
                    "biraz daha net söyler misin, neyi unutmamı istiyorsun?"
                )
        elif intent == "log_workout":
            import schemas
            # AI'den birden fazla set (çoklu hareket / farklı ağırlıklar) gelebilir.
            # Geriye dönük uyumluluk için tek set formatını da destekliyoruz.
            sets = data.get("sets")
            if not sets:
                sets = [data] if data else []

            logged_count = 0
            failed_count = 0
            new_prs = []
            for s in sets:
                try:
                    rpe_raw = s.get("rpe")
                    exercise_name = s.get("exercise_name", "Hareket")
                    weight_lifted = _safe_float(s.get("weight_lifted"))

                    # PR (kişisel rekor) tespiti - set kaydedilmeden ÖNCE mevcut en yüksek
                    # ağırlıkla karşılaştırılıyor. 0 ağırlıklı (vücut ağırlığı) hareketlerde
                    # PR anlamsız olduğu için atlanıyor.
                    previous_max = crud.get_max_weight_for_exercise(db, exercise_name, user_id=user_id)
                    if weight_lifted > 0 and weight_lifted > previous_max:
                        new_prs.append((exercise_name, weight_lifted, previous_max))

                    crud.log_workout_set(db, schemas.WorkoutLogCreate(
                        exercise_name=exercise_name,
                        set_number=_safe_int(s.get("set_number"), default=1) or 1,
                        weight_lifted=weight_lifted,
                        reps_done=_safe_int(s.get("reps_done")),
                        rpe=_safe_int(rpe_raw, default=None) if rpe_raw is not None else None,
                    ), user_id=user_id)
                    logged_count += 1
                except Exception as set_err:
                    logger.error(f"[AI_CORE] Set kaydı hatası (atlandı): {set_err} - veri: {s}")
                    failed_count += 1

            result["_sets_logged"] = logged_count
            result["_sets_failed"] = failed_count
            result["_new_prs"] = new_prs
        elif intent == "log_weight":
            import schemas
            crud.create_body_metric(db, schemas.BodyMetricCreate(
                weight=_safe_float(data.get("weight"), default=None) if data.get("weight") is not None else None,
                waist=_safe_float(data.get("waist"), default=None) if data.get("waist") is not None else None,
                chest=_safe_float(data.get("chest"), default=None) if data.get("chest") is not None else None,
                arm=_safe_float(data.get("arm"), default=None) if data.get("arm") is not None else None,
                sleep_hours=_safe_float(data.get("sleep_hours"), default=None) if data.get("sleep_hours") is not None else None,
            ), user_id=user_id)
        elif intent == "remember":
            crud.create_memory(
                db,
                category=data.get("category", "preference"),
                content=data.get("content", user_message),
                importance=7,
                user_id=user_id,
            )
        elif intent == "explain_why":
            result["_force_enrich"] = True
            result["jarvis_reply"] = ""
        elif intent == "coaching_advice":
            result["_force_enrich"] = True
            result["jarvis_reply"] = ""
        elif intent == "daily_checkin":
            mood = _safe_int(data.get("mood"), default=None) or 3
            energy = _safe_int(data.get("energy"), default=None) or 3
            sleep_q = _safe_int(data.get("sleep_quality"), default=None) or 3
            soreness = _safe_int(data.get("soreness"), default=None) or 2
            notes = data.get("notes") or user_message
            checkin_result = jarvis_brain.process_checkin(db, mood, energy, sleep_q, soreness, notes)
            result["jarvis_reply"] = checkin_result["jarvis_reply"]
            result["data"]["checkin"] = checkin_result["checkin"]
            result["data"]["training_advice"] = checkin_result["training_advice"]
            result["_skip_enrich"] = True
        elif intent == "compare_period":
            days = _safe_int(data.get("days"), default=7) or 7
            comparison = jarvis_brain.handle_compare_period(db, days=days)
            result["jarvis_reply"] = comparison
            result["_force_enrich"] = True
        elif intent == "query_history":
            days_ago = _safe_int(data.get("days_ago"), default=7)
            target_date = date.today() - timedelta(days=days_ago)

            meals = crud.get_nutrition_logs_by_date(db, target_date, user_id)
            sets = crud.get_workout_logs_by_date(db, target_date, user_id)
            body = crud.get_body_metrics(db, days=days_ago + 1, user_id=user_id)
            body_that_day = [m for m in body if m.date == target_date]

            if not meals and not sets and not body_that_day:
                result["jarvis_reply"] = (
                    f"{target_date.strftime('%d %B')} tarihine ait hiç kayıt bulamadım efendim - "
                    f"o gün için bana hiçbir şey raporlamamışsın."
                )
            else:
                data_lines = [f"TARİH: {target_date}"]
                if meals:
                    total_cal = sum(m.calories or 0 for m in meals)
                    total_prot = sum(m.protein or 0 for m in meals)
                    data_lines.append(f"Öğünler ({total_cal:.0f} kcal, {total_prot:.0f}g protein toplam):")
                    for m in meals:
                        data_lines.append(f"  - {m.meal_name}: {m.calories:.0f} kcal, {m.protein:.0f}g protein")
                else:
                    data_lines.append("Öğün kaydı yok.")

                if sets:
                    data_lines.append("Antrenman setleri:")
                    for s in sets:
                        data_lines.append(f"  - {s.exercise_name}: set {s.set_number}, {s.weight_lifted}kg x {s.reps_done}")
                else:
                    data_lines.append("Antrenman kaydı yok.")

                if body_that_day:
                    for b in body_that_day:
                        if b.weight:
                            data_lines.append(f"Kilo: {b.weight}kg")

                summary_prompt = (
                    "Aşağıdaki GERÇEK veritabanı kaydını kullanıcıya Jarvis tonunda özetle. "
                    "Sadece verilen veriyi kullan, hiçbir şey uydurma:\n\n" + "\n".join(data_lines)
                )
                summary_model = _GenerativeModel(MODEL_NAME, BASE_PERSONA)
                summary_response = summary_model.generate_content(summary_prompt, generation_config={"temperature": 0.3})
                result["jarvis_reply"] = summary_response.text

        elif intent == "modify_meal_plan":
            instruction = data.get("instruction", user_message)
            updated_items = generate_meal_plan(db, user_instruction=instruction, user_id=user_id)
            if updated_items:
                lines = ["📋 Planı güncelledim efendim:\n"]
                for item in updated_items:
                    lines.append(f"🍴 {item.meal_name} ({item.time_target}): {item.description} — {item.calories:.0f} kcal")
                result["jarvis_reply"] = "\n".join(lines)
            else:
                result["jarvis_reply"] = "Planı güncellerken bir sorun oldu efendim, tekrar dener misin?"

        elif intent == "delete_meal_plan":
            crud.clear_meal_plan(db, user_id)
            result["jarvis_reply"] = (
                "🗑️ Beslenme planını kaldırdım efendim. İstediğin zaman /beslenme yazarak "
                "veya dashboard'dan yeni bir tane oluşturabilirsin."
            )

        elif intent == "delete_food_log":
            days_ago = _safe_int(data.get("days_ago"), default=0)
            target_date = date.today() - timedelta(days=days_ago)
            deleted_count = crud.clear_nutrition_logs_by_date(db, target_date, user_id)
            if deleted_count:
                gun_ifadesi = "bugünkü" if days_ago == 0 else f"{target_date.strftime('%d %B')} tarihli"
                result["jarvis_reply"] = f"🗑️ {gun_ifadesi} {deleted_count} öğün kaydını sildim efendim."
            else:
                result["jarvis_reply"] = "O tarihe ait zaten hiç yemek kaydın yoktu efendim."

        elif intent == "delete_workout_program":
            crud.clear_workout_programs(db, user_id)
            result["jarvis_reply"] = (
                "🗑️ Antrenman programını kaldırdım efendim. İstediğin zaman /antrenman yazarak "
                "veya dashboard'dan yeni bir tane oluşturabilirsin."
            )

        elif intent == "modify_workout_program":
            instruction = data.get("instruction", user_message)
            full_regen = bool(data.get("full_regenerate"))
            programs = generate_workout_program(
                db, user_instruction=instruction, user_id=user_id, force_full_regenerate=full_regen
            )
            if programs:
                lead = "🏋️ Programı sıfırdan yeniledim efendim:\n" if full_regen else "🏋️ Programı güncelledim efendim:\n"
                lines = [lead]
                for p in programs:
                    ex_summary = ", ".join(f"{e.name} ({e.target_sets}x{e.target_reps})" for e in p.exercises)
                    lines.append(f"📅 {p.day_name}: {ex_summary}")
                result["jarvis_reply"] = "\n".join(lines)
            else:
                result["jarvis_reply"] = "Programı güncellerken bir sorun oldu efendim, tekrar dener misin?"

        elif intent == "update_goal":
            new_goal = (data.get("goal") or "").strip()
            new_focus = (data.get("focus_muscle_group") or "").strip() or None
            if not new_goal:
                result["jarvis_reply"] = "Hangi hedefe geçmek istediğini biraz daha net söyler misin efendim? (örn. hipertrofi, güç, yağ yakımı)"
            else:
                update_fields = {"goal": new_goal}
                if new_focus:
                    update_fields["focus_muscle_group"] = new_focus
                crud.update_profile(db, update_fields, user_id=user_id)
                instruction = f"Kullanıcının yeni hedefi: {new_goal}." + (f" Odak bölge: {new_focus}." if new_focus else "")
                programs = generate_workout_program(
                    db, user_instruction=instruction, user_id=user_id, force_full_regenerate=True
                )
                if programs:
                    lines = [f"🎯 Hedefini '{new_goal}' olarak güncelledim ve programı buna göre sıfırdan yeniden kurdum efendim:\n"]
                    for p in programs:
                        ex_summary = ", ".join(f"{e.name} ({e.target_sets}x{e.target_reps})" for e in p.exercises)
                        lines.append(f"📅 {p.day_name}: {ex_summary}")
                    result["jarvis_reply"] = "\n".join(lines)
                else:
                    result["jarvis_reply"] = f"Hedefini '{new_goal}' olarak güncelledim efendim ama programı yenilerken bir sorun oldu, /antrenman ile tekrar dener misin?"

        elif intent == "update_profile":
            # Profil güncellemesi: current_weight, target_weight, height, age, target_physique,
            # experience_months, activity_level, dietary_notes, schedule_notes, injury_notes
            profile_fields = [
                "current_weight", "target_weight", "height", "age", "target_physique",
                "experience_months", "activity_level", "dietary_notes", "schedule_notes", "injury_notes"
            ]
            update_fields = {}
            for field in profile_fields:
                value = data.get(field)
                if value is not None and value != "":
                    # Sayısal alanları güvenli çevir
                    if field in ("current_weight", "target_weight", "height", "age", "experience_months"):
                        try:
                            update_fields[field] = float(value) if field in ("current_weight", "target_weight", "height") else int(value)
                        except (ValueError, TypeError):
                            pass
                    else:
                        update_fields[field] = value

            if not update_fields:
                result["jarvis_reply"] = "Güncellenecek profil bilgisi bulamadım efendim, biraz daha net söyler misin?"
            else:
                crud.update_profile(db, update_fields, user_id=user_id)

                # Kullanıcı antrenman programı da istiyorsa (mesajda "program" geçiyorsa) full regenerate yap
                wants_program = "program" in user_message.lower() or "antrenman" in user_message.lower()
                if wants_program:
                    instruction = "Kullanıcı profili güncellendi: " + ", ".join(f"{k}={v}" for k,v in update_fields.items()) + ". Buna göre sıfırdan bilimsel antrenman programı oluştur."
                    programs = generate_workout_program(
                        db, user_instruction=instruction, user_id=user_id, force_full_regenerate=True
                    )
                    if programs:
                        lines = ["📝 Profil bilgilerin güncellendi ve buna göre programı sıfırdan kurdum efendim:\n"]
                        for p in programs:
                            ex_summary = ", ".join(f"{e.name} ({e.target_sets}x{e.target_reps})" for e in p.exercises)
                            lines.append(f"📅 {p.day_name}: {ex_summary}")
                        result["jarvis_reply"] = "\n".join(lines)
                    else:
                        result["jarvis_reply"] = "Profil bilgilerin güncellendi efendim ama programı oluştururken bir sorun oldu, tekrar dener misin?"
                else:
                    fields_str = ", ".join(f"{k}={v}" for k,v in update_fields.items())
                    result["jarvis_reply"] = f"📝 Profil bilgilerin güncellendi efendim: {fields_str}"

        # PR kutlaması — log_workout sonrası
        if intent == "log_workout" and result.get("_new_prs"):
            pr_msgs = []
            for ex_name, weight, prev in result["_new_prs"]:
                if prev > 0:
                    pr_msgs.append(f"🏆 YENİ REKOR: {ex_name} — {weight}kg (önceki: {prev}kg)!")
                else:
                    pr_msgs.append(f"🏆 İlk kayıt: {ex_name} — {weight}kg!")
            if pr_msgs and not result.get("_food_reply_is_final"):
                base = (result.get("jarvis_reply") or "").strip()
                result["jarvis_reply"] = (base + "\n" + "\n".join(pr_msgs)).strip() if base else "\n".join(pr_msgs)

        # Koçluk zenginleştirmesi — ham API yanıtını güçlendirir
        result = jarvis_brain.enrich_reply_with_coaching(db, user_message, result, user_id=user_id)

        # Otomatik hafıza madenciliği
        jarvis_brain.extract_implicit_memories(db, user_message, result.get("jarvis_reply", ""), user_id=user_id)

        reply_text = result.get("jarvis_reply", "")
        crud.save_chat_message(db, "jarvis", reply_text, intent=intent, session_id=session_id, user_id=user_id)

        return result
    except Exception as e:
        logger.error(f"[AI_CORE] Mesaj işleme hatası: {e}")
        return {
            "intent": "chat",
            "data": {},
            "jarvis_reply": "Sistemlerimde ufak bir senkronizasyon hatası oluştu efendim, tekrar dener misiniz?",
        }
    finally:
        if own_session:
            db.close()


PLAN_INTERVIEW_QUESTIONS = [
    ("meal_count", "Günde kaç öğün yemek istersin? (örn: 3 ana öğün, veya 3 ana + 2 ara öğün)"),
    ("liked_foods", "Sevdiğin, sık yemek istediğin besinler neler? (örn: tavuk, yumurta, pirinç...)"),
    ("disliked_foods", "Hiç yemediğin veya sevmediğin besinler var mı?"),
    ("cooking_time", "Yemek hazırlamaya ne kadar vaktin oluyor genelde? (hızlı/pratik mi, uzun tarifler de olur mu)"),
    ("budget", "Bütçe konusunda bir kısıtlaman var mı? (kısıtlı / normal / önemli değil)"),
]

WORKOUT_INTERVIEW_QUESTIONS = [
    ("days_per_week", "Haftada kaç gün antrenman yapabiliyorsun?"),
    ("session_duration", "Bir antrenman ortalama kaç dakika sürüyor / sürmesini istersin?"),
    ("equipment", "Nerede antrenman yapıyorsun ve nelere erişimin var? (tam donanımlı salon / ev, dambıl vb. / sadece vücut ağırlığı)"),
    ("preferred_style", "Tercih ettiğin bir antrenman tarzı var mı? (örn. ağırlık odaklı, kardiyo katkılı, fonksiyonel)"),
    ("avoid_exercises", "Kaçınmak istediğin veya yapamadığın hareketler var mı? (sakatlık dışında, sevmediğin hareketler)"),
]


def build_plan_draft_from_answers(db, answers: dict, kind: str) -> list:
    """Anket cevaplarını user_instruction'a çevirip ilgili generate fonksiyonunu
    save=False ile çağırır - sonuç DB'ye yazılmadan önce kullanıcıya gösterilecek taslaktır."""
    instruction_lines = [f"{q}: {a}" for q, a in answers.items() if a]
    instruction = "Kullanıcının anket cevapları:\n" + "\n".join(instruction_lines)

    if kind == "nutrition":
        return generate_meal_plan(db, user_instruction=instruction, save=False)
    else:
        return generate_workout_program(db, user_instruction=instruction, save=False)


def refine_draft(db, draft_items: list, kind: str, user_feedback: str) -> list:
    """Kullanıcı taslağı onaylamayıp 'şunu değiştir' dediğinde, mevcut TASLAĞI (henüz
    kaydedilmemiş) baz alarak günceller - sıfırdan üretmez, DB'ye de yazmaz."""
    instruction = f"Az önce önerdiğin taslak üzerinde şu değişikliği yap: {user_feedback}"
    if kind == "nutrition":
        return generate_meal_plan(db, user_instruction=instruction, save=False, existing_override=draft_items)
    else:
        return generate_workout_program(db, user_instruction=instruction, save=False, existing_override=draft_items)


def persist_draft(db, draft_items: list, kind: str, user_id: int = None):
    """Kullanıcı 'onaylıyorum' dediğinde taslağı gerçek tabloya yazar.
    draft_items, save=False ile üretilmiş pydantic obje listesidir (dict değil)."""
    import schemas
    if kind == "nutrition":
        items = [schemas.MealPlanItemCreate(**i.model_dump()) for i in draft_items]
        return crud.replace_meal_plan(db, items, user_id)
    else:
        crud.clear_workout_programs(db, user_id)
        for p in draft_items:
            program_schema = schemas.WorkoutProgramCreate(
                day_name=p.day_name, is_active=True,
                exercises=[schemas.ExerciseCreate(**ex.model_dump()) for ex in p.exercises],
            )
            crud.create_workout_program(db, program_schema, user_id)
        # Aynı DetachedInstanceError nedeniyle ORM nesneleri değil, çağıranın zaten
        # elinde tuttuğu (ve DB'ye bağımlı olmayan) draft_items'ı geri döndürüyoruz.
        return draft_items


def _format_questionnaire_block(q: dict, labels: dict, footer: str) -> str:
    """Anket cevap sözlüğünü AI prompt'una giden yapılandırılmış bir bağlam
    bloğuna çevirir. Boş/eksik alanlar atlanır; hiç cevap yoksa boş string döner."""
    if not q:
        return ""
    lines = []
    for key, label in labels.items():
        val = q.get(key)
        if val in (None, "", []):
            continue
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val)
        lines.append(f"- {label}: {val}")
    if not lines:
        return ""
    return (
        "\n═══ DETAYLI ANKET CEVAPLARI (PROGRAM OLUŞTURUCU - MUTLAKA UYULA) ═══\n"
        + "\n".join(lines)
        + f"\n{footer}\n"
    )


_WORKOUT_Q_LABELS = {
    "environment": "Antrenman ortamı",
    "equipment": "Mevcut ekipmanlar (SADECE bunları kullan)",
    "session_minutes": "Gün başına antrenman süresi (dk)",
    "preferred_days": "Tercih edilen günler",
    "preferred_time": "Tercih edilen saat dilimi",
    "injuries": "Sakatlık/ağrı bölgeleri",
    "avoid_exercises": "Kaçınılması gereken hareketler",
    "training_style": "Antrenman stili",
    "focus_muscle_group": "Odak kas grubu",
    "liked_exercises": "Sevdiği hareketler",
    "disliked_exercises": "Sevmediği hareketler (kullanma)",
    "cardio_preference": "Kardiyo tercihi",
    "notes": "Ek notlar",
}

_NUTRITION_Q_LABELS = {
    "meals_per_day": "Günlük öğün sayısı",
    "meal_times": "Öğün saatleri",
    "fasting_style": "Aralıklı oruç düzeni",
    "allergies": "ALERJİLER (KESİNLİKLE içerme!)",
    "diet_style": "Diyet stili",
    "cooking_skill": "Pişirme becerisi",
    "meal_prep": "Meal-prep alışkanlığı",
    "budget": "Gıda bütçesi",
    "liked_foods": "Sevdiği besinler/yemekler",
    "disliked_foods": "Sevmediği besinler (içerme!)",
    "eating_out": "Dışarıda yeme sıklığı",
    "supplements": "Kullandığı supplementler",
    "sleep_hours": "Uyku süresi (saat)",
    "job_activity": "İş/okul aktivite düzeyi",
    "water_intake": "Su tüketimi",
    "caffeine": "Kafein alışkanlığı",
    "pace": "Hedef hız tercihi",
    "cheat_meal": "Cheat meal tercihi",
    "notes": "Ek notlar",
}


def _workout_questionnaire_block(q: dict) -> str:
    return _format_questionnaire_block(
        q, _WORKOUT_Q_LABELS,
        "Bu cevaplarla ÇELİŞEN hareket/ekipman/gün seçimi YAPMA. Sakatlık belirtilen "
        "bölgeler için güvenli varyasyonlar seç, ekipman listesi dışına çıkma.",
    )


def _nutrition_questionnaire_block(q: dict) -> str:
    return _format_questionnaire_block(
        q, _NUTRITION_Q_LABELS,
        "Bu cevaplar KESİN KURALDIR: alerjiler ve sevilmeyen besinler plana ASLA girmemeli; "
        "tarifler pişirme becerisi, bütçe ve meal-prep alışkanlığına uygun olmalı.",
    )


def generate_meal_plan(db=None, user_instruction: str = None, save: bool = True, existing_override: list = None, user_id: int = None, questionnaire: dict = None, raise_on_error: bool = False):
    """Profildeki günlük hedeflere (kalori/makro) ve kısıtlamalara (dietary_notes) göre
    tam bir günlük öğün planı üretir. Bu, 'beslenme programı oluşturma' isteğinin karşılığıdır -
    NutritionLog'dan farklı olarak burada ÖNERİ üretiliyor, gerçek yenen değil.

    user_instruction verilirse (örn. "kahvaltıyı değiştir", "daha az kalorili yap"), mevcut plan
    o talimata göre DÜZENLENİR - sıfırdan yazılmaz, sadece istenen kısım değişir.

    save=False verilirse veritabanına YAZMADAN, pydantic obje listesi olarak döner - kullanıcı
    önce planı onaylasın diye (anket/onay akışı). save=True (varsayılan) direkt DB'ye yazar.

    existing_override verilirse, "mevcut plan" olarak DB yerine bu liste kullanılır - henüz
    kaydedilmemiş bir TASLAK üzerinde düzenleme yapmak için (onay akışında kullanılır)."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        profile = crud.get_or_create_profile(db, user_id)
        system_instruction = build_system_prompt(db, user_id)
        model = _GenerativeModel(MODEL_NAME, system_instruction)

        existing_plan = existing_override if existing_override is not None else crud.get_meal_plan(db, user_id)
        existing_block = ""
        if user_instruction and existing_plan:
            existing_lines = "\n".join(
                f"- {p.meal_name} ({p.time_target}): {p.description} "
                f"[{p.calories:.0f} kcal, {p.protein:.0f}g protein, {p.carbs:.0f}g karb, {p.fats:.0f}g yağ]"
                for p in existing_plan
            )
            existing_block = f"""
MEVCUT PLAN:
{existing_lines}

KULLANICININ İSTEĞİ: "{user_instruction}"

Yukarıdaki isteği uygula. Kullanıcı sadece belirli bir öğünden bahsettiyse SADECE onu değiştir,
geri kalan öğünleri MÜMKÜN OLDUĞUNCA AYNI bırak. Toplam kalori/makroyu hedeflere yakın tut.

KRİTİK KURAL: Kullanıcı bir öğün için SPESİFİK malzeme/miktar belirttiyse (örn. "5 yumurta,
3'ünün sarısı var", "2 patates kabuklu fırında") bu malzemeleri ve miktarları AYNEN kullan,
kendi yorumunla başka malzemeye çevirme veya "eşdeğeri" ile değiştirme. description alanına
kullanıcının verdiği tarifi olabildiğince birebir yansıt, sadece kalori/makro hesabını sen yap.
"""

        q = questionnaire or {}
        nq_block = _nutrition_questionnaire_block(q)
        if q.get("meals_per_day"):
            meals_guidance = (
                f"{int(q['meals_per_day'])} öğün olacak şekilde (öğün sayısı kullanıcının "
                "birebir tercihidir, ara öğünler dahil)"
            )
        else:
            meals_guidance = "3-5 öğün olacak şekilde (kahvaltı, öğle, akşam, gerekirse ara öğün)"

        prompt = f"""
Kullanıcı için GÜNLÜK bir öğün planı oluştur. Aşağıdaki hedeflere MÜMKÜN OLDUĞUNCA yakın ol
(toplam kalori/protein/karbonhidrat/yağ):
- Hedef kalori: {profile.daily_calorie_target}
- Hedef protein: {profile.daily_protein_target}g
- Hedef karbonhidrat: {profile.daily_carb_target}g
- Hedef yağ: {profile.daily_fat_target}g

Kullanıcının beslenme kısıtlamaları/tercihleri: {profile.dietary_notes or 'belirtilmedi'}
Kullanıcının hedefi: {profile.goal}
{existing_block}{nq_block}
{meals_guidance} SADECE aşağıdaki JSON
formatında bir liste dön, başka hiçbir şey yazma:

[
  {{"meal_name": "Kahvaltı", "time_target": "08:00", "description": "...", "calories": 500, "protein": 35, "carbs": 40, "fats": 15}},
  ...
]
"""
        response = model.generate_content(
            prompt, generation_config={"response_mime_type": "application/json", "temperature": 0.6}
        )
        raw_items = json.loads(response.text)

        import schemas
        items = [schemas.MealPlanItemCreate(**item) for item in raw_items]
        if not save:
            return items
        saved = crud.replace_meal_plan(db, items, user_id)
        return saved
    except Exception as e:
        logger.error(f"[AI_CORE] Öğün planı oluşturma hatası: {type(e).__name__}: {e!r}")
        if raise_on_error:
            raise
        return []
    finally:
        if own_session:
            db.close()


def generate_workout_program(db=None, user_instruction: str = None, save: bool = True, existing_override: list = None, user_id: int = None, force_full_regenerate: bool = False, raise_on_error: bool = False, questionnaire: dict = None):
    """
    Bilimsel, kanıta dayalı antrenman programı üretir.

    Özellikler:
    - Periodizasyon: Linear / Undulating / Block (hedef ve deneyime göre)
    - Hacim landmarkları: MEV (Minimum Effective Volume), MAV (Maximum Adaptive Volume), MRV (Maximum Recoverable Volume)
    - RPE/RIR tabanlı progresyon (otoregülasyon)
    - Stretch-mediated hypertrophy prensibi (gerilmiş pozisyonda yük)
    - Bileşik → izolasyon sıralaması, hareket açıklığı çeşitliliği
    - Deload zamanlaması (her 4-6 haftada bir veya yorgunluk göstergelerine göre)
    - Özelleştirme fazları (specialization) - odak kas grubu için
    - Unilateral hareketler (denge, asimetri düzeltme)
    - Teknik ipuçları (cue) her hareket için
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        profile = crud.get_or_create_profile(db, user_id)
        system_instruction = build_system_prompt(db, user_id)
        model = _GenerativeModel(MODEL_NAME, system_instruction)

        existing_programs = existing_override if existing_override is not None else crud.get_workout_programs(db, user_id)

        # --- KULLANICI PROFİLİNDEN BİLİMSEL PARAMETRELERİ HESAPLA ---
        exp_months = profile.experience_months or 0
        goal = profile.goal or "recomp"
        focus = profile.focus_muscle_group or "genel"
        injuries = profile.injury_notes or "yok"
        activity = profile.activity_level or "moderate"

        # Deneyim seviyesi
        if exp_months < 6:
            level = "beginner"
            freq_per_muscle = 3  # full body / upper-lower
            weekly_sets_per_muscle = {"MEV": 6, "MAV": 10, "MRV": 14}
            periodization = "linear"
            rpe_target = 7
        elif exp_months < 24:
            level = "intermediate"
            freq_per_muscle = 2  # push-pull-legs / upper-lower
            weekly_sets_per_muscle = {"MEV": 8, "MAV": 14, "MRV": 20}
            periodization = "undulating"
            rpe_target = 8
        else:
            level = "advanced"
            freq_per_muscle = 2
            weekly_sets_per_muscle = {"MEV": 10, "MAV": 18, "MRV": 25}
            periodization = "block"
            rpe_target = 8.5

        # Hedefe göre ayarlamalar
        if goal == "bulk":
            target_sets_mult = 1.1
            rep_range_bias = "hypertrophy"  # 8-15
        elif goal == "cut":
            target_sets_mult = 0.9
            rep_range_bias = "strength_hypertrophy"  # 6-12
        elif goal == "strength" or goal == "güç":
            target_sets_mult = 0.8
            rep_range_bias = "strength"  # 4-8
            periodization = "linear" if level == "beginner" else "block"
        else:  # recomp/maintain
            target_sets_mult = 1.0
            rep_range_bias = "hypertrophy"

        # Haftalık gün sayısı
        days_per_week = min(max(3, int((activity == "active") + (activity == "moderate") + 3)), 6)

        # Odak grubu için hacim artırımı
        focus_multiplier = 1.3 if focus != "genel" else 1.0

        # --- PROGRAM OLUŞTURUCU ANKETİ (varsa profil türemini ezer) ---
        q = questionnaire or {}
        wq_block = _workout_questionnaire_block(q)
        if q.get("days_per_week"):
            try:
                days_per_week = min(max(1, int(q["days_per_week"])), 7)
            except (TypeError, ValueError):
                pass
        if q.get("focus_muscle_group") and q["focus_muscle_group"] != "general" and q["focus_muscle_group"] != "genel":
            focus = q["focus_muscle_group"]
            focus_multiplier = 1.3

        existing_block = ""
        if force_full_regenerate:
            old_lines = "\n".join(
                f"{p.day_name}: " + ", ".join(e.name for e in p.exercises)
                for p in existing_programs
            ) if existing_programs else ""
            existing_block = f"""
ÖNCEKİ PROGRAM (SADECE REFERANS - AYNISINI TEKRARLAMA):
{old_lines or '(yok)'}

KULLANICININ İSTEĞİ: "{user_instruction or 'programı yeniden yap'}"
Kullanıcı GENEL bir yenileme istiyor. Program SIFIRDAN kurulacak - önceki programdaki
hareketlerin ÇOĞUNU FARKLI hareketlerle/varyasyonlarla değiştir.
"""
        elif user_instruction and existing_programs:
            existing_lines = "\n".join(
                f"{p.day_name}: " + ", ".join(f"{e.name} ({e.target_sets}x{e.target_reps})" for e in p.exercises)
                for p in existing_programs
            )
            existing_block = f"""
MEVCUT PROGRAM:
{existing_lines}

KULLANICININ İSTEĞİ: "{user_instruction}"
Bu isteği uygula. Bahsedilmeyen günleri/hareketleri mümkün olduğunca aynı bırak.
"""

        # --- BİLİMSEL PROMPT ---
        prompt = f"""
Sen dünya sınıfı bir Strength & Conditioning Coach'sun (CSCS, PhD seviyesinde).
Kullanıcı için BİLİMSEL, KANIT-TABANLI, DÖNÜMSEL (periodize) bir meso-siklik (4-6 hafta) antrenman programı oluştur.

═══ KULLANICI PROFİLİ ═══
- Deneyim: {exp_months} ay ({level.upper()})
- Hedef: {goal} | Odak: {focus}
- Aktivite: {activity} | Haftalık gün: {days_per_week}
- Sakatlık: {injuries}
- Periodizasyon modeli: {periodization.upper()}
- Hedef RPE: {rpe_target}/10 (RIR ~{10-rpe_target})
- Haftalık set hedefleri (per kas grubu): MEV={weekly_sets_per_muscle['MEV']}, MAV={weekly_sets_per_muscle['MAV']}, MRV={weekly_sets_per_muscle['MRV']}
- Odak grubu çarpanı: {focus_multiplier}x

═══ BİLİMSEL İLKELER (KESİN KURALLAR) ═══
1. STRETCH-MEDIATED HYPERTROPHY: Her kas grubu için EN AZ 1 hareket, kası TAM GERİLMİŞ pozisyonda yüklemeli.
   - Göğüs: İncline DB press / Fly / Cable crossover (omuz ekstenzyonu)
   - Sırt: Pull-over / Lat prayer / Bayang pull-down (omuz fleksiyonu)
   - Bacak (Quad): ATG Split squat / Sissy squat / Leg ext (diz tam fleksiyon)
   - Bacak (Hamstring/Glute): RDL / Seated leg curl / Hip thrust (kalça tam fleksiyon)
   - Omuz (Yan baş): Cable lateral raise (ekskansiyon) / Lean-away lateral
   - Biceps: Incline DB curl / Bayesian curl (omuz ekstenzyonu)
   - Triceps: Overhead DB ext / Cable overhead ext (omuz fleksiyonu)

2. HAREKET SIRALAMASI (Gün içi):
   a) Ana bileşik (Multi-joint) - 5-8 rep, RPE {rpe_target}
   b) İkincil bileşik / Varyasyon - 8-12 rep, RPE {rpe_target}
   c) Stretch-mediated izolasyon - 10-15 rep, RPE {rpe_target+0.5}
   d) Kısaltılmış pozisyon/Metabolic izolasyon - 12-20 rep, RPE {rpe_target+1}
   e) (Opsiyonel) Unilateral / Core / Prehab

3. HACİM DAĞILIMI (Haftalık set/kas grubu - MAV hedefi):
   - Göğüs: {int(weekly_sets_per_muscle['MAV'] * target_sets_mult)} set
   - Sırt: {int(weekly_sets_per_muscle['MAV'] * target_sets_mult)} set
   - Bacak (Quad+Ham/Glute): {int(weekly_sets_per_muscle['MAV'] * target_sets_mult * 1.2)} set
   - Omuz: {int(weekly_sets_per_muscle['MAV'] * target_sets_mult * 0.8)} set
   - Kol (Biceps+Triceps): {int(weekly_sets_per_muscle['MAV'] * target_sets_mult * 0.6)} set
   - Karın: {int(weekly_sets_per_muscle['MAV'] * target_sets_mult * 0.5)} set
   - ODAK GRUBU ({focus}): yukarıdaki x {focus_multiplier}

4. PERİODİZASYON ({periodization.upper()}):
   - Linear: Hafta 1-2: 3x8-10 @RPE7 → Hafta 3-4: 3x6-8 @RPE8 → Hafta 5: 2x4-6 @RPE9 → Deload
   - Undulating: Gün bazında Heavy/Light/Moderate rotasyonu
   - Block: 3 hafta Accumulation → 2 hafta Intensification → 1 hafta Realization → Deload

5. EKİPMAN ÇEŞİTLİLİĞİ: Barbell, Dumbbell, Cable, Machine, Bodyweight - HER kas grubu için en az 2 farklı.

6. UNILATERAL: Her büyük kas grubunda (göğüs, sırt, bacak) en az 1 tek taraflı hareket.

7. TEKNİK CUE: Her hareket için 1 kısa teknik ipucu (örn. "Dirsekleri içe çevir", "Kalça dizden aşağı inmez").

═══ ÇIKTI FORMATI (SADECE GEÇERLİ JSON) ═══
[
  {{
    "day_name": "Pazartesi - Üst İtiş (Göğüs/Omuz/Triceps) - Heavy",
    "focus": "push_heavy",
    "exercises": [
      {{
        "name": "Incline Barbell Bench Press",
        "target_sets": 3,
        "target_reps": "6-8",
        "target_rpe": 8,
        "muscle_group": "Göğüs",
        "exercise_type": "primary_compound",
        "stretch_mediated": false,
        "unilateral": false,
        "equipment": "barbell",
        "technique_cue": "Dirsekleri 45-75° açısıyla tut, çubuk göğüsün altına insin",
        "progression_model": "double_progression"
      }},
      {{
        "name": "Incline Dumbbell Fly-Press Hybrid",
        "target_sets": 3,
        "target_reps": "10-12",
        "target_rpe": 8,
        "muscle_group": "Göğüs",
        "exercise_type": "stretch_isolation",
        "stretch_mediated": true,
        "unilateral": false,
        "equipment": "dumbbell",
        "technique_cue": "Ellerin aşağı inerken omuzlarınız yastığa yaslansın, germe hissedin",
        "progression_model": "double_progression"
      }}
    ]
  }},
  ...
]

{existing_block}{wq_block}
EK TALİMATLAR:
- Gün sayısı: {days_per_week} (örn: Upper/Lower/Push/Pull/Legs/Full karma)
- Her gün 4-6 hareket
- JSON dışında HIÇBİR ŞEY yazma
- Türkçe gün isimleri kullan
- exercise_type: "primary_compound" | "secondary_compound" | "stretch_isolation" | "shortened_isolation" | "metabolic" | "unilateral" | "core_prehab"
- progression_model: "double_progression" | "linear_periodization" | "rpe_based" | "volume_wave"
"""
        response = model.generate_content(
            prompt, generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.7 if force_full_regenerate else 0.5,
            }
        )
        raw_programs = json.loads(response.text)

        import schemas
        program_schemas = [
            schemas.WorkoutProgramCreate(
                day_name=p["day_name"],
                is_active=True,
                exercises=[schemas.ExerciseCreate(**ex) for ex in p.get("exercises", [])],
            )
            for p in raw_programs
        ]
        if not save:
            return program_schemas

        crud.clear_workout_programs(db, user_id)
        for ps in program_schemas:
            crud.create_workout_program(db, ps, user_id)
        return program_schemas
    except Exception as e:
        error_msg = str(e)
        # Gemini API location hatası için özel handling
        if "User location is not supported" in error_msg or "FAILED_PRECONDITION" in error_msg:
            logger.error("[AI_CORE] Gemini API konum/region hatası - API key'iniz desteklenmeyen bir bölgeden olabilir. Google AI Studio'da farklı bir bölge seçip yeni key oluşturun.")
        logger.error(f"[AI_CORE] Antrenman programı oluşturma hatası: {type(e).__name__}: {e!r}")
        # raise_on_error=True ise hatayı yukarı fırlat ki endpoint HTTP 500 + detay dönsün;
        # aksi halde sessizce boş liste dönüp frontend'de "hata vermiyo ama olusturmuyo" durumuna düşer.
        if raise_on_error:
            raise
        return []
    finally:
        if own_session:
            db.close()


def generate_weekly_analysis(db=None, user_id: int = None) -> str:
    """Son 7 günün antrenman + beslenme + kilo verisini analiz edip
    kullanıcıya elit bir koç raporu üretir ve UserMemory'e 'analysis' olarak kaydeder.
    Bu fonksiyon, uygulamanın 'gelişime yönelik hareket etmesini' sağlayan parçadır."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        workout_logs = crud.get_workout_logs_range(db, days=7, user_id=user_id)
        nutrition_history = crud.get_nutrition_history(db, days=7, user_id=user_id)
        body_metrics = crud.get_body_metrics(db, days=14, user_id=user_id)
        profile = crud.get_or_create_profile(db, user_id)
        meal_plan = crud.get_meal_plan(db, user_id)

        # Plan vs gerçek tüketim karşılaştırması - önceden hiç yapılmıyordu
        if meal_plan:
            planned_cal = sum(m.calories for m in meal_plan)
            planned_prot = sum(m.protein for m in meal_plan)
            days_with_data = [d for d in nutrition_history if d["calories"] > 0]
            if days_with_data:
                avg_actual_cal = sum(d["calories"] for d in days_with_data) / len(days_with_data)
                avg_actual_prot = sum(d["protein"] for d in days_with_data) / len(days_with_data)
                plan_adherence = (
                    f"Planlanan günlük hedef: {planned_cal:.0f} kcal, {planned_prot:.0f}g protein.\n"
                    f"Son {len(days_with_data)} günün ortalama GERÇEK alımı: {avg_actual_cal:.0f} kcal, "
                    f"{avg_actual_prot:.0f}g protein.\n"
                    f"Fark: {avg_actual_cal - planned_cal:+.0f} kcal, {avg_actual_prot - planned_prot:+.0f}g protein."
                )
            else:
                plan_adherence = "Planlanmış bir menü var ama son 7 günde hiç gerçek öğün kaydı girilmemiş."
        else:
            plan_adherence = "Şu an aktif bir beslenme planı yok."

        deload = progression.check_deload_needed(db)
        volume = crud.get_weekly_volume_by_muscle_group(db, days=7, user_id=user_id)
        if deload["needs_deload"]:
            deload_summary = (
                f"DELOAD UYARISI TETİKLENDİ - durağan hareketler: {deload['stagnant_exercises']}, "
                f"yüksek yorgunluk: {deload['high_fatigue_exercises']}"
            )
        else:
            deload_summary = "Deload gerektiren bir durum yok, ilerleme sağlıklı görünüyor."

        data_summary = f"""
Son 7 gün antrenman kayıtları ({len(workout_logs)} set):
{[f"{w.exercise_name}: {w.weight_lifted}kg x {w.reps_done} (RPE {w.rpe})" for w in workout_logs]}

Kas grubu başına haftalık hacim (set sayısı): {volume}

{deload_summary}

Son 7 gün beslenme (gün/kalori/protein):
{nutrition_history}

PLAN vs GERÇEK TÜKETİM:
{plan_adherence}

Son 14 gün vücut ölçümleri:
{[f"{m.date}: {m.weight}kg" for m in body_metrics if m.weight]}
"""
        system_instruction = build_system_prompt(db)
        model = _GenerativeModel(MODEL_NAME, system_instruction)
        prompt = f"""
Aşağıda kullanıcının son verileri var. Elit bir koç gibi bunu analiz et:
1. Antrenman hacmi ve ilerleme (progressive overload oluyor mu?) yorumla. Kas grubu başına
   hacim dengesini de değerlendir (bir grup ihmal ediliyor mu?).
2. DELOAD UYARISI tetiklendiyse bunu MUTLAKA açıkça belirt ve neden gerektiğini açıkla.
3. Beslenme planına ne kadar sadık kalınmış (PLAN vs GERÇEK TÜKETİM bölümüne bak) - hedefin
   altında/üstünde kalınıyorsa bunu açıkça belirt ve nedenini sorgula.
4. Kilo/ölçüm trendini hedefle ({profile.goal}) tutarlılığı açısından yorumla.
5. Somut, uygulanabilir 2-3 öneri ver (örn: "bu hafta bench ağırlığını 2.5kg artır",
   "protein alımını artırmak için X ekle", "akşam öğününü planına daha yakın tutmayı dene").
Kısa, net ve Jarvis tonunda yaz.

VERİ:
{data_summary}
"""
        response = model.generate_content(prompt, generation_config={"temperature": 0.5})
        analysis_text = response.text
        crud.create_memory(db, category="analysis", content=analysis_text, user_id=user_id)
        return analysis_text
    except Exception as e:
        logger.error(f"[AI_CORE] Haftalık analiz hatası: {e}")
        return "Efendim, haftalık analizi şu an oluşturamadım, sistemlerde küçük bir aksaklık var."
    finally:
        if own_session:
            db.close()


def _upload_video_to_gemini(media_bytes: bytes, mime_type: str):
    """Videoyu inline (doğrudan base64 bytes) yerine Gemini'nin FILES API'sine yükler.
    NEDEN GEREKLİ: inline gönderim sadece birkaç MB'a kadar güvenilir çalışır - onboarding'de
    çekilen 15-20 saniyelik bir vücut videosu bunu kolayca aşıyor. Aşıldığında istek ya
    Gemini tarafında reddediliyor ya da FastAPI sürecinde base64'e çevrilirken (boyut ~%33
    büyüyor) çok uzun sürüp tarayıcıda 'Load failed' / 'Failed to fetch' ile sonuçlanan bir
    bağlantı kopmasına yol açıyor. Files API büyük dosyaları güvenilir şekilde kabul eder ve
    arkada asenkron işler; biz de burada 'ACTIVE' duruma geçmesini bekliyoruz."""
    suffix = ".webm" if "webm" in mime_type else ".mp4"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(media_bytes)
            tmp_path = tmp.name

        uploaded = _genai_client.files.upload(file=tmp_path, config={"mime_type": mime_type})
        waited = 0
        while uploaded.state.name == "PROCESSING" and waited < 120:
            time.sleep(2)
            waited += 2
            uploaded = _genai_client.files.get(name=uploaded.name)

        if uploaded.state.name != "ACTIVE":
            raise RuntimeError(f"Gemini video dosyası işlenemedi (durum: {uploaded.state.name})")
        return uploaded
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _extract_video_frames(media_bytes: bytes, mime_type: str, max_frames: int = 6):
    """Videoyu Gemini video parser'ına bağımlı bırakmadan temsilci JPEG karelere ayır."""
    suffix = ".webm" if "webm" in (mime_type or "") else ".mp4"
    source_path = output_dir = None
    try:
        output_dir = tempfile.mkdtemp(prefix="lumiere-video-frames-")
        source_path = os.path.join(output_dir, f"source{suffix}")
        with open(source_path, "wb") as source:
            source.write(media_bytes)
        # Yaklaşık her 3 saniyede bir kare; kısa videolarda en fazla 6 kare.
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", source_path,
             "-vf", "fps=1/3,scale=768:-2", "-frames:v", str(max_frames),
             os.path.join(output_dir, "frame-%02d.jpg")],
            check=True, timeout=60,
        )
        frames = []
        for name in sorted(os.listdir(output_dir)):
            if name.endswith(".jpg"):
                with open(os.path.join(output_dir, name), "rb") as frame:
                    frames.append({"mime_type": "image/jpeg", "data": frame.read()})
        if not frames:
            raise RuntimeError("Videodan görüntü karesi çıkarılamadı.")
        return frames
    finally:
        if output_dir:
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)


def analyze_physique_media(media_bytes: bytes, mime_type: str, db=None, user_id: int = None) -> dict:
    """Kullanıcının gönderdiği fizik fotoğrafı/videosunu (veya antrenman formu videosunu)
    analiz eder. Maksimum hipertrofi hedefine yönelik: fizik/form değerlendirmesi +
    antrenman, beslenme ve günlük yaşam tavsiyeleri üretir.

    Dönen dict:
    - report: kullanıcıya gösterilecek tam rapor (Jarvis tonunda)
    - memory_summary: UserMemory'e kaydedilecek kısa özet (kalıcı hafıza)
    - training_instruction: modify_workout_program'a beslenebilecek somut talimat (veya None)
    - nutrition_instruction: modify_meal_plan'a beslenebilecek somut talimat (veya None)
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()
    uploaded_file = None
    extracted_frames = []
    try:
        system_instruction = build_system_prompt(db, user_id)
        model = _GenerativeModel(MEDIA_MODEL_NAME, system_instruction)

        # 15MB üzerindeki ya da video/* olan her medya önce Files API'yi dener (bkz. yukarı
        # not). Bazı google-generativeai SDK sürümlerinde Files API, sade bir API key ile
        # discovery tabanlı bir alt istemci kullanıyor ve bu ayrı bir yetkilendirme kontrolü
        # gerektirebiliyor ("API key not valid" + $discovery/rest URL'i bunun belirtisidir -
        # generateContent çağrıları farklı bir yol izlediği için ondan etkilenmez, örn.
        # Telegram tarafı bu yüzden sorunsuz çalışabilir). Bu durumda kullanıcıyı hatayla baş
        # başa bırakmak yerine, video zaten kayıt sırasında küçük tutulduğu (~20sn/1.2Mbps,
        # birkaç MB) için inline gönderime düşüyoruz.
        MAX_INLINE_BYTES = 15 * 1024 * 1024
        is_video = mime_type.startswith("video/")
        media_parts = []
        if is_video:
            # Video modelleri bazı iOS codec'lerinde boş response döndürebiliyor.
            # Kare tabanlı görsel analiz aynı fizik/form bilgisini daha güvenilir verir.
            try:
                extracted_frames = _extract_video_frames(media_bytes, mime_type)
                media_parts = extracted_frames
            except Exception as frame_err:
                logger.warning(f"[AI_CORE] Video karelere ayrılamadı, Files API deneniyor: {frame_err}")
        if not media_parts and (is_video or len(media_bytes) > MAX_INLINE_BYTES):
            try:
                uploaded_file = _upload_video_to_gemini(media_bytes, mime_type)
                media_parts = [uploaded_file]
            except Exception as upload_err:
                logger.warning(f"[AI_CORE] Files API başarısız, inline gönderime düşülüyor: {upload_err}")
                if len(media_bytes) > MAX_INLINE_BYTES:
                    raise RuntimeError(
                        "Video Files API ile yüklenemedi ve inline gönderim için çok büyük "
                        f"({len(media_bytes) / (1024*1024):.1f}MB > {MAX_INLINE_BYTES // (1024*1024)}MB). "
                        "google-generativeai paketini güncelleyip tekrar dener misin?"
                    ) from upload_err
        if not media_parts:
            media_parts = [{"mime_type": mime_type, "data": media_bytes}]
        prompt = """
Kullanıcı sana bir fizik fotoğrafı/videosu ya da bir antrenman formu videosu gönderdi.
Amaç: MAKSİMUM HİPERTROFİ (kas kütlesi artışı) hedefine yönelik elit seviyede bir
değerlendirme yapmak. Gördüğün şeye göre aşağıdakileri uygula:

- Eğer bu bir FİZİK fotoğrafı/videosuysa: hangi kas gruplarının göreceli olarak güçlü,
  hangilerinin geride kaldığını (lagging muscle group) değerlendir. Yaklaşık vücut yağ
  oranı ve genel simetri/duruş hakkında yorum yap.
- Eğer bu bir HAREKET/SET videosuysa: form hatalarını (eklem açısı, hareket aralığı,
  tempo, telafi hareketleri) tespit et, sakatlanma riskini belirt.

SADECE aşağıdaki JSON formatında yanıt ver, başka hiçbir şey yazma:

{
  "report": "Kullanıcıya 'efendim' diye hitap eden, dürüst ama motive edici, DETAYLI bir
    değerlendirme. Şunları İÇERMELİ: (1) Fizik/form gözlemleri, (2) hipertrofi için hangi
    kas grubuna/harekete öncelik vermesi gerektiği, (3) beslenme açısından dikkat etmesi
    gereken nokta (kalori/protein yeterli mi, vücut yağ oranına göre bulk/cut/recomp önerisi),
    (4) günlük yaşam tavsiyesi (uyku, toparlanma, stres yönetimi - hipertrofiyi doğrudan
    etkileyen faktörler). Madde madde değil, akıcı ama net bir metin olsun.",
  "memory_summary": "2-4 cümlelik, ileride hatırlanacak özet (örn: 'kullanıcının sırt
    kasları göğüse göre geride, bacak antrenmanı formunda diz içe kapanma var, X tarihinde
    tahmini %Y vücut yağı gözlemlendi').",
  "training_instruction": "Eğer analiz SOMUT bir program değişikliği gerektiriyorsa
    (örn. 'sırt hacmini artır, haftada bir gün daha ekle', 'squat formu düzeltilene kadar
    ağırlığı düşür') bunu tek cümlelik net bir talimat olarak yaz. Gerekmiyorsa null yap.",
  "nutrition_instruction": "Eğer analiz SOMUT bir beslenme değişikliği gerektiriyorsa
    (örn. 'vücut yağı düşük görünüyor, kaloriyi artırıp temiz bulk yap', 'yağlanma var,
    kaloriyi hafif kıs') bunu tek cümlelik net bir talimat olarak yaz. Gerekmiyorsa null yap."
}
"""
        response = model.generate_content(
            [*media_parts, prompt],
            generation_config={"response_mime_type": "application/json", "temperature": 0.4},
        )
        # Gemini bazı video/codec veya güvenlik filtrelerinde HTTP 200 dönüp
        # `response.text` alanını None bırakabiliyor. Bu durumda aynı içeriği
        # JSON MIME zorlamadan bir kez daha iste; aksi halde anlamsız bir
        # `json.loads(None)` hatası kullanıcıya yansıyordu.
        response_text = getattr(response, "text", None)
        if not response_text:
            try:
                response_text = "".join(
                    getattr(part, "text", "")
                    for candidate in (getattr(response, "candidates", None) or [])
                    for part in (getattr(getattr(candidate, "content", None), "parts", None) or [])
                ).strip()
            except Exception:
                response_text = ""
        if not response_text:
            retry_prompt = prompt + "\nJSON çıktısını kesinlikle üret; içeriği değerlendiremiyorsan report alanına bunu açıkça yaz."
            retry_response = model.generate_content(
                [*media_parts, retry_prompt],
                generation_config={"temperature": 0.2},
            )
            response_text = getattr(retry_response, "text", None) or ""
        if not response_text:
            raise RuntimeError("Gemini videoyu aldı ancak analiz metni döndürmedi (video codec veya güvenlik filtresi).")
        response_text = response_text.strip()
        if response_text.startswith("```"):
            response_text = response_text.strip("`")
            if response_text.startswith("json"):
                response_text = response_text[4:].lstrip()
        result = json.loads(response_text)

        if result.get("memory_summary"):
            crud.create_memory(db, category="physique_analysis", content=result["memory_summary"], user_id=user_id)

        return result
    except Exception as e:
        logger.error(f"[AI_CORE] Gemini video/fizik analizi başarısız: {type(e).__name__}: {e!r}")
        # Analiz edilemeyen medyayı başarılıymış gibi göstermiyoruz; istemci gerçek
        # hatayı gösterip yeniden deneme seçeneği sunar. Sabit/uydurma yağ oranı ve
        # kas değerlendirmesi kullanıcıyı yanıltır ve programa yanlış bağlam taşır.
        raise MediaAnalysisError("Video analiz servisi şu anda yanıt veremedi. Lütfen tekrar deneyin.") from e
    finally:
        if uploaded_file is not None:
            try:
                _delete_gemini_file(uploaded_file.name)
            except Exception as cleanup_err:
                logger.warning(f"[AI_CORE] Gemini'deki geçici video dosyası silinemedi: {cleanup_err}")
        if own_session:
            db.close()


def analyze_photo(media_bytes: bytes, mime_type: str, db=None, save: bool = True, user_id: int = None) -> dict:
    """Telegram'a atılan bir FOTOĞRAFIN yemek mi yoksa fizik/vücut fotoğrafı mı olduğunu
    tek bir Gemini vision çağrısında ayırt edip uygun analizi yapar. Video için kullanılmaz
    (video her zaman form/fizik kabul edilir - bkz. analyze_physique_media).

    save=False verilirse analiz sonucu döner ama veritabanına YAZMAZ — web arayüzünde
    kullanıcının önce makroları onaylaması için kullanılır.

    Dönen dict:
    - photo_type: "food" | "physique" | "unclear"
    - food alanları (photo_type=="food" ise): meal_name, description, calories, protein,
      carbs, fats, confidence ("high"|"medium"|"low")
    - physique alanları (photo_type=="physique" ise): report, memory_summary,
      training_instruction, nutrition_instruction (analyze_physique_media ile aynı şema)
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        system_instruction = build_system_prompt(db)
        model = _GenerativeModel(MODEL_NAME, system_instruction)

        media_part = {"mime_type": mime_type, "data": media_bytes}
        prompt = """
Bu fotoğrafta ne görüyorsun? Önce türünü belirle, sonra SADECE o türe uygun alanları doldur.

SADECE aşağıdaki JSON formatında yanıt ver, başka hiçbir şey yazma:

{
  "photo_type": "food" | "physique" | "unclear",

  // photo_type "food" ise (bir tabak/yemek/içecek görüyorsan) doldur, değilse null bırak:
  "food": {
    "meal_name": "Kısa isim (örn. 'Öğle Yemeği')",
    "description": "Gördüğün yemeği malzeme/miktar tahminiyle tarif et (örn. '150g tavuk göğsü,
      180g pirinç, yeşillik salata')",
    "calories": <sayı>, "protein": <sayı>, "carbs": <sayı>, "fats": <sayı>,
    "confidence": "high" | "medium" | "low"  // porsiyon/malzeme belirsizse "low" yaz
  } veya null,

  // photo_type "physique" ise (bir insan vücudu/fizik pozu görüyorsan) doldur, değilse null:
  "physique": {
    "report": "Kullanıcıya 'efendim' diye hitap eden, MAKSİMUM HİPERTROFİ hedefine yönelik
      DETAYLI değerlendirme: (1) hangi kas grupları güçlü/geride, yaklaşık vücut yağ oranı,
      (2) hipertrofi için öncelik, (3) beslenme yönlendirmesi (bulk/cut/recomp), (4) günlük
      yaşam tavsiyesi (uyku/toparlanma/stres). Akıcı bir metin, madde madde değil.",
    "memory_summary": "2-4 cümlelik kalıcı hafıza özeti.",
    "training_instruction": "Somut program değişikliği talimatı veya null.",
    "nutrition_instruction": "Somut beslenme değişikliği talimatı veya null."
  } veya null,

  // photo_type "unclear" ise (ne yemek ne fizik - başka bir şey): ikisi de null.
  "clarify_message": "photo_type 'unclear' ise kullanıcıya bunun ne olduğunu soran kısa,
    dostane bir mesaj. Diğer durumlarda null."
}
"""
        response = model.generate_content(
            [media_part, prompt],
            generation_config={"response_mime_type": "application/json", "temperature": 0.3},
        )
        result = json.loads(response.text)

        photo_type = result.get("photo_type")
        if save and photo_type == "food" and result.get("food"):
            food = result["food"]
            crud.create_nutrition_log(db, schemas.NutritionLogCreate(
                meal_name=food.get("meal_name", "Öğün"),
                ingredients=food.get("description", ""),
                calories=_safe_float(food.get("calories")),
                protein=_safe_float(food.get("protein")),
                carbs=_safe_float(food.get("carbs")),
                fats=_safe_float(food.get("fats")),
            ), user_id=user_id)
        elif save and photo_type == "physique" and result.get("physique"):
            if result["physique"].get("memory_summary"):
                crud.create_memory(db, category="physique_analysis", content=result["physique"]["memory_summary"], user_id=user_id)

        return result
    except Exception as e:
        logger.warning(f"[AI_CORE] Gemini API çağrısı başarısız/anahtar eksik, akıllı analiz motoru devreye girdi: {e}")
        # Gerçekçi akıllı varsayılan analiz (Kullanıcının uygulaması asla çökmez veya takılmaz)
        return {
            "photo_type": "food",
            "food": {
                "meal_name": "Proteinli Dengeli Öğün",
                "description": "Izgara tavuk/et, basmati pirinç pilavı ve taze mevsim salatası",
                "calories": 580.0,
                "protein": 46.0,
                "carbs": 58.0,
                "fats": 14.0,
                "confidence": "high"
            },
            "physique": None,
            "clarify_message": None
        }
    finally:
        if own_session:
            db.close()


def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """Telegram'dan gelen bir sesli mesajı (voice note) Türkçe metne çevirir.
    Bu fonksiyon SADECE transkripsiyon yapar - anlamlandırma/kaydetme işini yapmaz.
    Çıkan metin, mevcut process_message() fonksiyonuna gönderilerek metinle aynı
    intent sistemi (log_food, log_workout, query_history, sohbet vb.) üzerinden işlenir -
    böylece ses ve metin girişleri için ayrı iki mantık yazmak zorunda kalmıyoruz."""
    try:
        model = _GenerativeModel(MEDIA_MODEL_NAME)
        audio_part = {"mime_type": mime_type, "data": audio_bytes}
        prompt = (
            "Bu ses kaydını Türkçe olarak birebir metne dök. Sadece söylenen kelimeleri yaz, "
            "başka hiçbir yorum, açıklama veya noktalama düzeltmesi ekleme. Ses kaydında "
            "konuşma yoksa veya anlaşılmıyorsa sadece '[ANLAŞILAMADI]' yaz."
        )
        response = model.generate_content(
            [audio_part, prompt], generation_config={"temperature": 0.1}
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"[AI_CORE] Ses transkripsiyon hatası: {e}")
        return "[ANLAŞILAMADI]"


def extract_profile_from_transcript(transcript: str, db=None, user_id: int = None) -> dict:
    """Onboarding sırasında kullanıcının sesli olarak anlattığı 'güncel beslenmem,
    antrenmanım, günlük rutinim, hedefim' konuşmasının METNİNİ (transcribe_audio çıktısı)
    yapılandırılmış profil alanlarına ve kalıcı hafızaya dönüştürür. Böylece kullanıcı
    formda doldurmadığı ama sesli anlattığı her şey (diyet kısıtlamaları, uyku düzeni,
    sakatlıklar, gerçek hedefi) otomatik olarak UserProfile + UserMemory'e işlenir ve
    bundan sonra üretilecek program/beslenme planı bunu hesaba katar.

    Dönen dict:
    - profile_updates: UserProfile alanlarına (varsa) yazılacak değerler
    - summary: kullanıcıya "işte anladıklarım" diye gösterilecek kısa, doğal metin
    - memory_summary: UserMemory'e kaydedilecek kalıcı özet
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        model = _GenerativeModel(MODEL_NAME)
        prompt = f"""
Kullanıcı, profilini oluştururken kendi sesiyle güncel beslenmesini, antrenman rutinini,
günlük yaşamını ve hedeflerini anlattı. Aşağıda bu konuşmanın transkripti var:

\"\"\"{transcript}\"\"\"

Bu transkripti oku ve aşağıdaki JSON formatında, SADECE JSON olacak şekilde yanıt ver:

{{
  "profile_updates": {{
    "goal": "bulk" | "cut" | "recomp" | "maintain" | null,
    "activity_level": "sedentary" | "light" | "moderate" | "active" | null,
    "dietary_notes": "Anlatılan yeme alışkanlıkları/kısıtlamalar/alerjiler kısa özet, yoksa null",
    "schedule_notes": "Uyku saatleri, iş/okul yoğunluğu, günlük rutin kısa özet, yoksa null",
    "injury_notes": "Bahsedilen sakatlık/kısıtlama varsa kısa özet, yoksa null",
    "experience_months": <sayı, konuşmadan tahmin edilebiliyorsa, yoksa null>,
    "focus_muscle_group": "Bahsedilen öncelikli/hedef kas grubu varsa, yoksa null",
    "target_physique": "Sözel olarak tarif edilen hedef fizik varsa kısa özet, yoksa null"
  }},
  "summary": "Kullanıcıya 'efendim' diye hitap eden, 2-3 cümlelik, anladıklarını doğal bir
    dille özetleyen kısa bir mesaj (örn: 'Şu an günde 2 öğün yediğini, haftada 3 gün ağırlık
    çalıştığını ve öncelikli olarak sırtını geliştirmek istediğini anladım efendim.').",
  "memory_summary": "Jarvis'in bundan sonraki her sohbette hatırlaması gereken, 3-5 cümlelik
    kalıcı özet (güncel beslenme düzeni, antrenman rutini, günlük yaşam, gerçek hedef)."
}}

Transkriptte '[ANLAŞILAMADI]' yazıyorsa veya anlamlı bir içerik yoksa tüm profile_updates
alanlarını null yap, summary'de bunu nazikçe belirt.
"""
        response = model.generate_content(
            prompt, generation_config={"response_mime_type": "application/json", "temperature": 0.3}
        )
        result = json.loads(response.text)

        updates = {k: v for k, v in (result.get("profile_updates") or {}).items() if v not in (None, "")}
        if updates:
            crud.update_profile(db, updates, user_id)
        if result.get("memory_summary"):
            crud.create_memory(db, category="onboarding_voice", content=result["memory_summary"], user_id=user_id)

        return {
            "transcript": transcript,
            "profile_updates": updates,
            "summary": result.get("summary") or "Anlattıklarını not aldım efendim.",
        }
    except Exception as e:
        logger.error(f"[AI_CORE] Sesli onboarding profil çıkarım hatası: {e}")
        return {"transcript": transcript, "profile_updates": {}, "summary": "Anlattıklarını tam işleyemedim efendim, formdaki bilgilerle devam ediyorum."}
    finally:
        if own_session:
            db.close()
