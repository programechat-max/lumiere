"""
Bilimsel kaynak katmanı — küratörlü çekirdek (her üretimde deterministik) +
PubMed canlı sorgu (yalnızca program üretiminde, cache'li, hata halinde sessiz
fallback). Her hareket için evidence_refs (PMID) üretir.
"""
import logging
from urllib.parse import quote

from sqlalchemy.orm import Session

from models import ResearchNote
from knowledge.cache import TTL_PUBMED, cached
from config import settings

logger = logging.getLogger(__name__)

PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


# --- Küratörlü çekirdek (Faz 3): alanın sağlam bulguları, PMID'li ---
# Seed verisi seed_data.py'de tutulur; bu modül okuma + canlı sorgu yapar.

def get_research_context(db: Session, topics: list[str] | None = None, target_muscle_group: str | None = None, limit: int = 12) -> str:
    """Küratörlü aktif notları öncelik sırasıyla prompt metnine çevirir.
    Deterministik ve gecikmesiz - program üretiminin temel bilimsel bağlamı."""
    query = db.query(ResearchNote).filter(ResearchNote.is_active == True)  # noqa: E712
    if topics:
        query = query.filter(ResearchNote.topic.in_(topics))
    if target_muscle_group:
        query = query.filter(
            (ResearchNote.target_muscle_group == None) | (ResearchNote.target_muscle_group.ilike(f"%{target_muscle_group}%"))  # noqa: E711
        )
    notes = query.order_by(ResearchNote.relevance_score.desc()).limit(limit).all()
    if not notes:
        return ("Bilimsel bağlam tablosu boş - MEV/MAV/MRV hacim landmarkları, çoğu kas için "
                "haftada 2x'i pratik hacim dağıtımı olarak ve progressive overload ilkelerini kullan; "
                "frekansın hacim eşitken kesin üstün olduğunu iddia etme.")
    lines = [f"- {n.title}: {n.summary}" + (f" KURAL: {n.finding_rule}" if n.finding_rule else "") +
             (f" [PMID: {n.evidence_refs}]" if n.evidence_refs else "") for n in notes]
    return "\n".join(lines)


def _pubmed_client_params() -> dict:
    params = {"tool": "lumiere", "email": settings.PUBMED_EMAIL} if settings.PUBMED_EMAIL else {}
    return params


def fetch_pubmed_summaries(query: str, limit: int = 5) -> list[dict] | None:
    """PubMed esearch+efetch ile son 5 yılın en alakalı makale özetlerini çeker.
    Hata/yapılandırılmamış durumda None döner (küratörlü çekirdek yeterli)."""
    if requests is None or not settings.PUBMED_ENABLED:
        return None
    cache_key = f"knowledge:pubmed:{query.lower().strip()}:{limit}"
    def _producer():
        try:
            # NCBI: mindate formatı YYYY veya YYYY/MM/DD olabilir (kibar alt sınır filtresi)
            search_params = {
                **_pubmed_client_params(),
                "db": "pubmed",
                "term": query,
                "retmax": limit,
                "datetype": "pdat",
                "mindate": "2016/01/01",
                "sort": "relevance",
                "retmode": "json",
            }
            resp = requests.get(f"{PUBMED_BASE_URL}/esearch.fcgi", params=search_params, timeout=8)
            if resp.status_code != 200:
                logger.warning("[PUBMED] esearch başarısız status=%s", resp.status_code)
                return None
            id_list = resp.json().get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return None
            summary_params = {
                **_pubmed_client_params(),
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json",
            }
            sresp = requests.get(f"{PUBMED_BASE_URL}/esummary.fcgi", params=summary_params, timeout=8)
            if sresp.status_code != 200:
                return None
            result = sresp.json().get("result", {})
            summaries = []
            for pmid in id_list:
                doc = result.get(pmid)
                if not doc:
                    continue
                summaries.append({
                    "pmid": pmid,
                    "title": doc.get("title", "")[:300],
                    "journal": doc.get("source", ""),
                    "year": doc.get("pubdate", "")[:4],
                })
            return summaries or None
        except Exception as exc:
            logger.warning("[PUBMED] API erişilemedi (küratörlü çekirdekle devam): %s", exc)
            return None
    return cached(cache_key, ttl=TTL_PUBMED, producer=_producer)


def get_focus_evidence_block(db: Session, focus_muscle_group: str | None, focus_topic: str | None = None) -> str:
    """Odak kas grubuna özel blok: küratörlü not + (varsa) PubMed canlı özetler.
    Yalnızca program üretiminde çağrılır (kullanıcı onaylı hibrit strateji)."""
    lines = []
    # 1) Küratörlü (deterministik)
    curated = get_research_context(db, target_muscle_group=focus_muscle_group, limit=6)
    if curated and not curated.startswith("Bilimsel bağlam tablosu boş"):
        lines.append(f"BİLGİ KATMANI - Odak grup ({focus_muscle_group}) küratörlü bulgular:\n{curated}")
    # 2) PubMed canlı (cache'li, niş konu)
    if focus_topic or focus_muscle_group:
        live_query = focus_topic or f"{focus_muscle_group} hypertrophy resistance training"
        live = fetch_pubmed_summaries(live_query, limit=4)
        if live:
            live_lines = [f"- {s['title']} ({s['journal']} {s['year']}) [PMID:{s['pmid']}]" for s in live]
            lines.append("CANLI BİLİMSEL SORGU (PubMed):\n" + "\n".join(live_lines))
    return "\n\n".join(lines) if lines else ""
