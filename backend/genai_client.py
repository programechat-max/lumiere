"""
Ortak Google GenAI Client ve Model Sarmalayıcı — hem ai_core hem jarvis_brain tarafından kullanılır.
Bu dosya döngüsel import sorununu çözmek için oluşturuldu.
"""
import os
import tempfile
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY") or ""
API_KEY = API_KEY.strip() or None
_genai_client = genai.Client(api_key=API_KEY) if API_KEY else None


def _env_model(name: str, default: str) -> str:
    """Boş string olarak set edilmiş env değişkenlerini 'tanımsız' sayar.
    (.env içinde `GEMINI_MODEL=` şeklinde boş bırakıldığında os.getenv boş string
    döner ve geçersiz model adıyla API çağrısı yapılıp her şey bozuluyordu.)"""
    val = (os.getenv(name) or "").strip()
    return val or default


MODEL_NAME = _env_model("GEMINI_MODEL", "gemini-2.5-flash")
MEDIA_MODEL_NAME = _env_model("GEMINI_MEDIA_MODEL", "gemini-2.5-flash")
# 503/429 (yuksek talep / kota) hatalarinda devreye giren yedek model:
FALLBACK_MODEL_NAME = _env_model("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")

# Retry ayarlari: gecici API hatalarinda ustel beklemeyle yeniden dener
_MAX_ATTEMPTS = 3
_RETRY_DELAYS = (3, 7, 15)  # saniye


def _is_transient_error(exc: Exception) -> bool:
    """Google API'nin gecici hatalari (503 yuksek talep, 429 kota, 500, kesilen baglanti)."""
    msg = str(exc).upper()
    return any(
        token in msg
        for token in ("503", "429", "500", "UNAVAILABLE", "HIGH DEMAND", "OVERLOADED",
                      "RATE LIMIT", "RESOURCE_EXHAUSTED", "TIMEOUT", "CONNECTION")
    )


def ai_configured() -> bool:
    """Gemini API anahtarı yapılandırılmış mı? Frontend /api/status üzerinden
    bunu öğrenip kullanıcıya net bir yönlendirme gösterebilir."""
    return _genai_client is not None


class _GenerativeModel:
    """Eski google.generativeai.GenerativeModel arayüzünü yeni google-genai
    SDK'sı üzerine ince bir sarmalayıcı olarak taklit eder."""

    def __init__(self, model_name: str = MODEL_NAME, system_instruction: str = None):
        self.model_name = model_name
        self.system_instruction = system_instruction

    def generate_content(self, contents, generation_config: dict = None):
        if _genai_client is None:
            raise RuntimeError("GEMINI_API_KEY tanımlı değil - .env dosyasını kontrol et.")

        cfg = {}
        if self.system_instruction:
            cfg["system_instruction"] = self.system_instruction
        if generation_config:
            if "response_mime_type" in generation_config:
                cfg["response_mime_type"] = generation_config["response_mime_type"]
            if "temperature" in generation_config:
                cfg["temperature"] = generation_config["temperature"]

        config = genai_types.GenerateContentConfig(**cfg) if cfg else None

        # 1) Birincil model ustel beklemeyle denenir (503/429 gibi gecici hatalarda)
        last_exc = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return _genai_client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                last_exc = exc
                if not _is_transient_error(exc) or attempt == _MAX_ATTEMPTS - 1:
                    break
                time.sleep(_RETRY_DELAYS[attempt])

        # 2) Yedek model denenir (ayni hata tekrarlarsa)
        if self.model_name != FALLBACK_MODEL_NAME:
            try:
                return _genai_client.models.generate_content(
                    model=FALLBACK_MODEL_NAME,
                    contents=contents,
                    config=config,
                )
            except Exception:
                pass  # yedek de basarisizsa orijinal hatayi firlat

        raise last_exc


def _upload_video_to_gemini(media_bytes: bytes, mime_type: str):
    """Videoyu yeni SDK Files API'sine yükler ve ACTIVE olana kadar bekler."""
    suffix = ".webm" if "webm" in mime_type else ".mp4"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(media_bytes)
            tmp_path = tmp.name

        uploaded = _genai_client.files.upload(file=tmp_path, config={"mime_type": mime_type})
        waited = 0
        while uploaded.state and uploaded.state.name == "PROCESSING" and waited < 120:
            time.sleep(2)
            waited += 2
            uploaded = _genai_client.files.get(name=uploaded.name)

        if not uploaded.state or uploaded.state.name != "ACTIVE":
            raise RuntimeError(f"Gemini video dosyası işlenemedi (durum: {getattr(uploaded.state, 'name', '?')})")
        return uploaded
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _delete_gemini_file(file_name: str):
    try:
        _genai_client.files.delete(name=file_name)
    except Exception:
        pass