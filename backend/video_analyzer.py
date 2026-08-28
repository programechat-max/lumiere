"""
İlerleme videosu analiz aracı.
ÖNEMLİ DEĞİŞİKLİK: Önceki sürüm analiz çıktısını custom_prompt.txt dosyasına yazıyordu
ama telegram_bot.py bu dosyayı hiç okumuyordu - yani analiz botu hiç etkilemiyordu.
Artık sonuç doğrudan veritabanındaki UserMemory tablosuna yazılıyor; ai_core.py bu
tabloyu her mesajda okuyup system prompt'a otomatik ekliyor. Böylece Jarvis videoyu
gerçekten "hatırlıyor".
"""
import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY or API_KEY.strip() == "":
    logger.error("KRİTİK HATA: .env dosyasından GEMINI_API_KEY okunamadı!")
    raise SystemExit(1)

genai.configure(api_key=API_KEY)

VIDEO_FOLDER = "user_videos"


def analyze_progress_video():
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER)
        logger.warning(f"{VIDEO_FOLDER} klasörü oluşturuldu, içine video koyup tekrar çalıştır.")
        return

    video_extensions = ('.mp4', '.avi', '.mov', '.mkv')
    videos = [f for f in os.listdir(VIDEO_FOLDER) if f.lower().endswith(video_extensions)]

    if not videos:
        logger.warning("Klasörde analiz edilecek video bulunamadı!")
        return

    latest_video_path = os.path.join(VIDEO_FOLDER, max(videos, key=lambda f: os.path.getmtime(os.path.join(VIDEO_FOLDER, f))))
    logger.info(f"Video sisteme alınıyor: {latest_video_path}")

    with open(latest_video_path, "rb") as video_file:
        video_bytes = video_file.read()

    video_parts = {
        "mime_type": "video/mp4" if latest_video_path.endswith('.mp4') else "video/quicktime",
        "data": video_bytes,
    }

    model = genai.GenerativeModel(model_name="gemini-3.1-flash-lite")
    analysis_prompt = """
    Sen 'Jarvis' adında elit bir fitness asistanısın. Kullanıcının gönderdiği bu ilerleme
    videosunu izle. Kullanıcı fiziksel formunu gösteriyor ve/veya sözel olarak durumunu anlatıyor olabilir.

    Şu iki bölümü KESİN OLARAK ayır:

    === RAPOR ===
    Kullanıcıya doğrudan hitap eden, "efendim" diye başlayan, fizik/gelişim yorumu içeren kısa bir rapor.

    === HAFIZA ===
    Bundan sonraki sohbetlerde Jarvis'in hatırlaması gereken, 2-4 cümlelik özet notlar
    (fiziksel gözlemler, kullanıcının sözel olarak belirttiği hedef/istek varsa).
    """

    response = model.generate_content([video_parts, analysis_prompt])
    full_text = response.text

    if "=== HAFIZA ===" in full_text:
        rapor = full_text.split("=== HAFIZA ===")[0].replace("=== RAPOR ===", "").strip()
        hafiza = full_text.split("=== HAFIZA ===")[1].strip()
    else:
        rapor = full_text
        hafiza = full_text

    print("\n" + "=" * 70)
    print("🤖 JARVIS VİDEO ANALİZ RAPORU".center(70))
    print("=" * 70 + "\n")
    print(rapor)
    print("\n" + "=" * 70 + "\n")

    # Veritabanına yaz - artık gerçekten kullanılıyor
    import crud
    from database import SessionLocal
    db = SessionLocal()
    try:
        crud.create_memory(db, category="video_analysis", content=hafiza)
        logger.info("Jarvis hafızası veritabanına yazıldı. Bir sonraki sohbette bunu hatırlayacak.")
    finally:
        db.close()


if __name__ == "__main__":
    analyze_progress_video()
