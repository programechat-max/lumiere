"""
Kanonik egzersiz kütüphanesi — AI hareketleri SADECE buradan seçer (kilitli),
ama gerçekten gerekli bir hareket kütüphanede yoksa pending_review=True ile
ekleyebilir (kaçış vanası). Kanonik isimler WorkoutLog eşleşmelerinin ve
progression.py string tabanlı overload önerilerinin tutarlı çalışmasını garanti eder.
"""
import logging
import re

from sqlalchemy.orm import Session

from models import ExerciseLibraryItem

logger = logging.getLogger(__name__)


def _norm(text: str) -> str:
    """Karşılaştırma için normalleştirme: küçük harf + fazla boşlukları at."""
    return " ".join((text or "").strip().lower().split())


# Exercise.exercise_type enum ile birebir uyumlu
VALID_TYPES = {"primary_compound", "secondary_compound", "stretch_isolation", "shortened_isolation", "metabolic", "unilateral", "core_prehab"}
VALID_EQUIPMENT = {"barbell", "dumbbell", "cable", "machine", "bodyweight", "kettlebell", "band"}


def search_library(db: Session, muscle_group: str | None = None, equipment: list[str] | None = None, exclude_contraindications: str | None = None) -> list[dict]:
    """Kütüphaneyi filtreleyerek döndürür. AI prompt'una girecek hareket ADAY havuzu."""
    query = db.query(ExerciseLibraryItem).filter(
        ExerciseLibraryItem.pending_review == False,  # noqa: E712
        ExerciseLibraryItem.evidence_level == "expert_curated",
    )
    if muscle_group:
        query = query.filter(ExerciseLibraryItem.muscle_group.ilike(f"%{muscle_group}%"))
    items = query.order_by(ExerciseLibraryItem.usage_count.desc()).all()

    if equipment:
        allowed = {e.lower().strip() for e in equipment}
        items = [i for i in items if (i.equipment or "bodyweight").lower() in allowed]

    if exclude_contraindications:
        notes = _norm(exclude_contraindications)
        contra_map = [
            (("diz", "knee", "quad tendon"), "knee"),
            (("omuz", "shoulder", "rotator"), "shoulder"),
            (("bel", "lower back", "lomber", "spine"), "lower_back"),
        ]
        banned = {tag for keywords, tag in contra_map if any(k in notes for k in keywords)}
        if banned:
            items = [
                i for i in items
                if not banned & {
                    _norm(t) for t in re.split(r"[,|]", i.contraindications or "") if t
                }
            ]
    return [_library_item_to_dict(i) for i in items]


def _library_item_to_dict(i: ExerciseLibraryItem) -> dict:
    return {
        "name": i.name,
        "aliases": i.aliases or "",
        "muscle_group": i.muscle_group,
        "exercise_type": i.exercise_type,
        "stretch_mediated": bool(i.stretch_mediated),
        "unilateral": bool(i.unilateral),
        "equipment": i.equipment or "bodyweight",
        "technique_cue": i.technique_cue or "",
        "rep_range_bias": i.rep_range_bias or "",
        "evidence_refs": i.evidence_refs or "",
        "selection_reason": i.selection_reason or "",
        "evidence_level": i.evidence_level or "unverified",
        "evidence_source": i.evidence_source or "",
    }


def format_exercise_pool(db: Session, equipment: list[str] | None = None, injury_notes: str | None = None) -> str:
    """Aday egzersiz havuzunu prompt metnine çevirir.

    Güvenilir aday yoksa modelin kendi hareketini uydurmasına izin verilmez;
    çağıran üretim akışı deterministik validator'da durmalıdır.
    """
    pool = search_library(db, equipment=equipment, exclude_contraindications=injury_notes)
    if not pool:
        return ("ÜRETİM DURDURULMALI: bu kas/ekipman/sakatlık kombinasyonu için "
                "onaylı egzersiz adayı bulunamadı. Kütüphane dışı hareket uydurma.")
    lines = [f"{p['name']} ({p['muscle_group']}, {p['exercise_type'] or 'isolation'}, {p['equipment']}"
             f"{', tek-taraf' if p['unilateral'] else ''}{', tam-germe' if p['stretch_mediated'] else ''})"
             for p in pool]
    return "\n".join(lines)


def match_exercise_name(db: Session, name: str) -> ExerciseLibraryItem | None:
    """AI'nin seçtiği hareket adını kütüphanedeki kanonik kayıtta eşleştir.
    Doğrudan eşleşme yoksa takma adlar üzerinden içerir-mantığıyla dener."""
    norm = _norm(name)
    if not norm:
        return None
    direct = db.query(ExerciseLibraryItem).filter(
        ExerciseLibraryItem.name.ilike(f"%{norm}%"),
        ExerciseLibraryItem.evidence_level == "expert_curated",
    ).first()
    if direct:
        return direct
    stem = norm[:-2] if len(norm) > 5 else norm
    qualified = (
        db.query(ExerciseLibraryItem)
        .filter(ExerciseLibraryItem.evidence_level == "expert_curated")
        .filter(ExerciseLibraryItem.aliases.ilike(f"%{stem}%") | ExerciseLibraryItem.name.ilike(f"%{stem}%"))
        .first()
    )
    if qualified:
        return qualified
    # Pending/legacy kaydı reconcile için bulabilmek, ikinci üretimde aynı
    # satırın çoğalmasını önler; validator bunu üretim adayı olarak reddeder.
    return db.query(ExerciseLibraryItem).filter(
        ExerciseLibraryItem.aliases.ilike(f"%{stem}%") | ExerciseLibraryItem.name.ilike(f"%{stem}%")
    ).first()


def reconcile_program_with_library(db: Session, raw_programs: list[dict]) -> tuple[list[dict], list[dict]]:
    """AI çıktısını kütüphaneyle uzlaştırır:
    1. Her hareketi kanonik adla eşleştir, eşleşenin ismini kanonik isimle değiştir
       (progression eşleşmesi için) ve evidence_refs'i zenginleştir.
    2. Kütüphanede olmayan hareketi pending_review=True ile tabloya ekle (kaçış vanası).
    Döndürür: (uzlaştırılmış_programlar, kaçış vanasıyla eklenen_hareketler)."""
    added = []
    for program in raw_programs:
        for ex in program.get("exercises", []):
            name = ex.get("name") or ""
            match = match_exercise_name(db, name)
            if match:
                # Kanonik isimle değiştir (tutarlılık), bilgileri zenginleştir
                if ex.get("name") != match.name:
                    logger.info("[EX_LIB] '%s' -> kanonik '%s' ile değiştirildi", ex.get("name"), match.name)
                ex["name"] = match.name
                if not ex.get("muscle_group"):
                    ex["muscle_group"] = match.muscle_group
                if not ex.get("evidence_refs") and match.evidence_refs:
                    ex["evidence_refs"] = match.evidence_refs
                match.usage_count += 1
            else:
                # Kaçış vanası: yeni hareketi pending_review ile kaydet
                if db.query(ExerciseLibraryItem).filter(ExerciseLibraryItem.name.ilike(f"%{_norm(name)}%")).first():
                    continue  # yarış durumu: başka kayıt arada ekledi
                item = ExerciseLibraryItem(
                    name=name[:120],
                    muscle_group=ex.get("muscle_group") or "Diğer",
                    exercise_type=ex.get("exercise_type") if ex.get("exercise_type") in VALID_TYPES else None,
                    stretch_mediated=bool(ex.get("stretch_mediated")),
                    unilateral=bool(ex.get("unilateral")),
                    equipment=ex.get("equipment") if ex.get("equipment") in VALID_EQUIPMENT else "bodyweight",
                    technique_cue=ex.get("technique_cue") or None,
                    evidence_refs=",".join(ex.get("evidence_refs") or []),
                    selection_reason=ex.get("selection_reason") or None,
                    pending_review=True,
                )
                db.add(item)
                db.commit()
                db.refresh(item)
                added.append({"name": item.name, "muscle_group": item.muscle_group})
                logger.info("[EX_LIB] Kaçış vanası: yeni hareket pending_review eklendi: %s", item.name)
    db.commit()
    return raw_programs, added
