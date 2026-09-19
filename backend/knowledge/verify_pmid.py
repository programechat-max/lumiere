"""PMID doğrulama motoru - FAZ 7 adım 5.

EvidenceTopic kayıtlarının key_studies'indeki PMID'leri NCBI E-utilities üzerinden
doğrular:
  1. PMID dolu kayıt  -> esummary ile PubMed başlığı alınır, saklanan başlıkla
     benzeşim karşılaştırılır (uydurma/yanlış atıf yakalar).
  2. PMID boş kayıt   -> esearch (yazar + başlık kelimeleri) ile aday bulunur,
     esummary başlık benzeşimi yeterince yüksekse --fix ile doldurulur (pmid + link).

Udurma atıf riski sıfırlanır: atıfsız konu ya doğrulanmış PMID taşır ya da
raporda "çözülemedi" olarak işaretlenir (elle kürasyon gerekir).

Kullanım:
    cd backend && ../.venv/bin/python -m knowledge.verify_pmid            # rapor
    cd backend && ../.venv/bin/python -m knowledge.verify_pmid --fix      # boş PMID'leri doldur
    cd backend && ../.venv/bin/python -m knowledge.verify_pmid --limit 5  # hızlı test
"""
from __future__ import annotations

import argparse
import difflib
import logging
import re
import time

from database import SessionLocal
from models import EvidenceTopic, ResearchNote

logger = logging.getLogger(__name__)

# ResearchNote başlıkları iddia özetidir, makale başlığının birebir kopyası
# değildir. Bu eşleşmeler editör tarafından doğrulanmış canonical kaynaklardır;
# diğer PMID'ler otomatik olarak doğrulanmış sayılmaz.
KNOWN_RESEARCH_PMIDS = {
    "27433992", "30558493",       # volume/frequency
    "36662126", "41646176",       # ROM / longer-muscle-length reviews
    "35044672",                    # periodization meta-analysis
    "28919335",                    # resistance exercise and sleep review
    "28698222", "36057893",        # protein meta-analyses
    "35873210", "38274324",        # umbrella review / deload trial
    "34560586", "31482093", "37914977",  # prehab / energy surplus
    "33009197", "33049982", "34170576", "35819335", "38970765",  # exercise-choice topics
    "38156065", "39809454", "40692697", "33312291", "18827329",  # calf, biceps, deltoid, trunk
}

# NCBI E-utilities (API anahtarı olmadan 3 istek/sn limiti - 0.5s uyku yeterli)
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
REQUEST_SLEEP_S = 0.5

# Başlık benzeşiminde önemsemeyecek genel kelimeler (benzeşim skoru saptırmasın)
_STOP_TITLE_WORDS = {
    "the", "and", "of", "in", "on", "with", "for", "after", "during", "versus",
    "vs", "a", "an", "to", "at", "by", "effect", "effects", "exercise",
    "training", "resistance", "study", "between",
}

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


def _norm_title(text: str) -> str:
    """Başlık benzeşimi için normalize eder: küçük harf, sadece harf/rakam/boşluk."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())).strip()


def _title_similarity(a: str, b: str) -> float:
    """İki başlık arasındaki benzeşim (0-1): difflib oranı ile anlamlı kelime
    kesişiminin ortalaması. Stop-kelimeler çıkarılır."""
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return 0.0
    ratio = difflib.SequenceMatcher(None, na, nb).ratio()
    wa = {w for w in na.split() if len(w) > 3 and w not in _STOP_TITLE_WORDS}
    wb = {w for w in nb.split() if len(w) > 3 and w not in _STOP_TITLE_WORDS}
    word_overlap = (len(wa & wb) / len(wa | wb)) if (wa or wb) else 0.0
    return round((ratio + word_overlap) / 2, 3)


def _esearch(term: str, retmax: int = 5) -> list[str]:
    """PubMed esearch: PMID listesi döner (hata halinde boş liste)."""
    if requests is None:
        return []
    try:
        resp = requests.get(
            f"{EUTILS_BASE}/esearch.fcgi",
            params={"db": "pubmed", "term": term, "retmode": "json", "retmax": retmax},
            timeout=10,
        )
        time.sleep(REQUEST_SLEEP_S)
        if resp.status_code != 200:
            return []
        return resp.json().get("esearchresult", {}).get("idlist", []) or []
    except Exception as exc:
        logger.warning("[VERIFY_PMID] esearch hatası (term=%s): %s", term, exc)
        return []


def _esummary(pmid: str) -> dict | None:
    """Tek PMID için esummary: {title, journal, pubdate} (hata halinde None)."""
    if requests is None:
        return None
    try:
        resp = requests.get(
            f"{EUTILS_BASE}/esummary.fcgi",
            params={"db": "pubmed", "id": pmid, "retmode": "json"},
            timeout=10,
        )
        time.sleep(REQUEST_SLEEP_S)
        if resp.status_code != 200:
            return None
        doc = resp.json().get("result", {}).get(str(pmid))
        if not doc:
            return None
        return {
            "title": doc.get("title", ""),
            "journal": (doc.get("source") or doc.get("fulljournalname") or ""),
            "pubdate": doc.get("pubdate", ""),
        }
    except Exception as exc:
        logger.warning("[VERIFY_PMID] esummary hatası (pmid=%s): %s", pmid, exc)
        return None


def _build_search_term(study: dict) -> str:
    """key_studies girdisinden PubMed sorgusu kurar: yazar soyadı + başlık kelimeleri.
    'Maeo et al.' -> Maeo[Author]; başlıktan stop-kelime dışı en fazla 5 kelime AND'lenir."""
    parts: list[str] = []
    authors = (study.get("authors") or "").split("et al")[0].strip().rstrip(",. ")
    surname = authors.split()[-1] if authors else ""
    if surname:
        parts.append(f"{surname}[Author]")
    title_words = []
    for w in _norm_title(study.get("title", "")).split():
        if len(w) > 3 and w not in _STOP_TITLE_WORDS and w not in title_words:
            title_words.append(w)
        if len(title_words) >= 5:
            break
    parts.extend(title_words)
    return " AND ".join(parts)


def _search_best_match(study: dict) -> dict | None:
    """esearch+esummary taraması: {'pmid','title','sim'} en iyi adayı döndürür ya da None."""
    ids = _esearch(_build_search_term(study), retmax=4)
    best: dict | None = None
    for pmid in ids:
        doc = _esummary(pmid)
        if not doc:
            continue
        sim = _title_similarity(study.get("title", ""), doc.get("title", ""))
        if best is None or sim > best["sim"]:
            best = {"pmid": pmid, "title": doc.get("title"), "sim": sim}
    return best


def verify_topic_pmid(study: dict) -> dict:
    """Tek key_studies girdisini doğrular/aday arar. Döner:
    {pmid, status: verified|mismatch|filled|unresolved|unreachable|no_api, remote_title, sim?}"""
    stored_pmid = (study.get("pmid") or "").strip()
    stored_title = study.get("title") or ""
    if requests is None:
        return {"pmid": stored_pmid, "status": "no_api", "remote_title": None}
    if stored_pmid:
        doc = _esummary(stored_pmid)
        if doc is None:
            return {"pmid": stored_pmid, "status": "unreachable", "remote_title": None}
        sim = _title_similarity(stored_title, doc.get("title", ""))
        if sim >= 0.45:
            return {"pmid": stored_pmid, "status": "verified", "remote_title": doc.get("title"), "sim": sim}
        # PMID dolu ama başlık uyuşmuyor: doğru atıf taranır, benzeşimi ≥0.75 aday
        # varsa run_verify --fix bu adayı mismatch düzeltmesi olarak yazar.
        best = _search_best_match(study)
        if best and best["sim"] >= 0.75 and best["pmid"] != stored_pmid:
            return {"pmid": best["pmid"], "status": "filled", "remote_title": best["title"], "sim": best["sim"]}
        return {"pmid": stored_pmid, "status": "mismatch", "remote_title": doc.get("title"), "sim": sim}
    # PMID boş -> esearch ile aday bul
    term = _build_search_term(study)
    if not term:
        return {"pmid": "", "status": "unresolved", "remote_title": None}
    ids = _esearch(term, retmax=4)
    best_pmid, best_title, best_sim = "", None, 0.0
    for pmid in ids:
        doc = _esummary(pmid)
        if not doc:
            continue
        sim = _title_similarity(stored_title, doc.get("title", ""))
        if sim > best_sim:
            best_pmid, best_title, best_sim = pmid, doc.get("title"), sim
    if best_pmid and best_sim >= 0.45:
        return {"pmid": best_pmid, "status": "filled", "remote_title": best_title, "sim": best_sim}
    return {"pmid": best_pmid or "", "status": "unresolved", "remote_title": best_title, "sim": best_sim}


def verify_research_note_refs(db, limit: int | None = None, fix: bool = False) -> dict:
    """ResearchNote PMID'lerini de EvidenceTopic'lerle aynı başlık kapısından geçirir.

    Önceden doğrulama yalnızca sohbet kanıt bankasını kapsıyordu; program
    üretiminde kullanılan ResearchNote kayıtları bu yüzden yanlış PMID taşıyabiliyordu.
    """
    rows = db.query(ResearchNote).order_by(ResearchNote.id.asc()).all()
    if limit:
        rows = rows[:limit]
    stats = {"verified": 0, "mismatch": 0, "unreachable": 0, "missing": 0}
    details = []
    for note in rows:
        raw = (note.evidence_refs or "").strip()
        pmids = [part.strip().removeprefix("PMID:").strip()
                 for part in raw.split(",") if part.strip().startswith("PMID:")]
        if not pmids:
            stats["missing"] += 1
            details.append({"note_id": note.id, "title": note.title, "status": "missing", "pmid": raw})
            continue
        remotes = [_esummary(pmid) for pmid in pmids]
        if not all(remotes):
            status = "unreachable"
            stats[status] += 1
            details.append({"note_id": note.id, "title": note.title, "status": status, "pmid": raw})
            continue
        status = "verified" if all(pmid in KNOWN_RESEARCH_PMIDS for pmid in pmids) else "mismatch"
        stats[status] += 1
        if fix and status != "verified":
            # Yanlış referansı düzeltmeye çalışıp yeni bir PMID uydurma. Kayıt
            # kaynak editörüne bırakılmak üzere atıfsız ama dürüst hale gelir.
            note.evidence_refs = None
            db.commit()
        details.append({"note_id": note.id, "title": note.title, "status": status,
                        "pmid": raw, "remote_title": [r.get("title") for r in remotes],
                        "sim": [_title_similarity(note.title, r.get("title", "")) for r in remotes]})
    return {"stats": stats, "details": details}


def run_verify(limit: int | None = None, fix: bool = False) -> dict:
    """Tüm aktif EvidenceTopic satırlarının key_studies'ini doğrular, rapor döner.
    fix=True ise: 'filled' PMID'leri ve benzeşimi ≥0.75 olan 'mismatch' düzeltmeleri
    (pmid + pubmed linki) tabloya yazar."""
    db = SessionLocal()
    stats = {"verified": 0, "filled": 0, "mismatch": 0, "unresolved": 0, "unreachable": 0, "no_api": 0}
    details: list[dict] = []
    try:
        query = db.query(EvidenceTopic).filter(EvidenceTopic.is_active.is_(True))
        rows = query.limit(limit).all() if limit else query.all()
        for topic in rows:
            studies = topic.key_studies or []
            changed = False
            for study in studies:
                res = verify_topic_pmid(study)
                status = res["status"]
                stats[status] = stats.get(status, 0) + 1
                study["_pmid_status"] = status
                if fix and status == "filled" and res["pmid"]:
                    study["pmid"] = res["pmid"]
                    study["link"] = f"https://pubmed.ncbi.nlm.nih.gov/{res['pmid']}/"
                    changed = True
                elif fix and status == "mismatch" and res.get("sim", 0) >= 0.75 and res["pmid"]:
                    # Yanlış PMID, benzeşimi yüksek doğrusuyla değiştirilir
                    study["pmid"] = res["pmid"]
                    study["link"] = f"https://pubmed.ncbi.nlm.nih.gov/{res['pmid']}/"
                    study["_pmid_status"] = "fixed_from_mismatch"
                    changed = True
                details.append({
                    "topic_id": topic.id, "topic": topic.topic,
                    "muscle_group": topic.muscle_group,
                    "authors": study.get("authors"), "year": study.get("year"),
                    "stored_title": (study.get("title") or "")[:80],
                    **res,
                })
            if changed:
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(topic, "key_studies")
                db.commit()
        research = verify_research_note_refs(db, limit=limit, fix=fix)
        for status, count in research["stats"].items():
            stats[f"research_{status}"] = count
        details.extend({"section": "research_notes", **item} for item in research["details"])
        return {"stats": stats, "details": details}
    finally:
        db.close()


def _print_report(result: dict) -> None:
    stats = result["stats"]
    print("\n=== PMID DOĞRULAMA RAPORU ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("-" * 60)
    for d in result["details"]:
        if d.get("section") == "research_notes":
            print(f"[{'✓' if d['status'] == 'verified' else '✗'}] ResearchNote #{d['note_id']} "
                  f"PMID={d.get('pmid') or 'BOŞ'} [{d['status']}] "
                  f"{(d.get('title') or '')[:90]}")
            continue
        mark = {"verified": "✓", "filled": "＋", "mismatch": "✗", "unresolved": "?",
                "unreachable": "!", "no_api": "×"}.get(d["status"], "·")
        sim_note = f" sim={d['sim']}" if d.get("sim") is not None else ""
        print(f"[{mark}] #{d['topic_id']} {d['topic']}({d['muscle_group'] or '-'}) "
              f"{d['authors']} {d['year']}: PMID={d['pmid'] or 'BOŞ'} [{d['status']}]{sim_note}")
        if d.get("remote_title") and d["status"] in ("mismatch", "filled"):
            print(f"      PubMed: {d['remote_title'][:90]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EvidenceTopic PMID doğrulama (NCBI E-utilities)")
    parser.add_argument("--fix", action="store_true", help="boş PMID'leri benzeşimle bulup doldur")
    parser.add_argument("--limit", type=int, default=None, help="işlenecek maksimum konu")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s: %(message)s")
    report = run_verify(limit=args.limit, fix=args.fix)
    _print_report(report)
