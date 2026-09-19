"""
Idempotent seed çalıştırıcı — bilgi katmanı tablolarını başlangıç verisiyle doldurur.

Çalıştırma: cd backend && python seed_knowledge.py
Idempotent: aynı isimli kayıt varsa dokunmaz (makro güncellemeleri elle müdahale
hakki gerektirdiği için üzerine YAZMAZ), sadece eksikleri ekler.
"""
import logging

from database import SessionLocal, migrate_schema
from models import FoodItem, ExerciseLibraryItem, ResearchNote, EvidenceTopic
from knowledge.seed_data import FOOD_SEED, FOOD_SEED_USDA, EXERCISE_SEED, RESEARCH_SEED
from knowledge.evidence_exercises import EVIDENCE_EXERCISES
from knowledge.evidence_topics import EVIDENCE_TOPICS

GENERAL_EXERCISE_EVIDENCE = "PMID:36662126,PMID:41646176"
GROUP_EXERCISE_EVIDENCE = {
    "Triceps": "PMID:35819335,PMID:36662126",
    "Hamstring & Glute": "PMID:33009197,PMID:41646176",
    "Göğüs": "PMID:33049982,PMID:36662126",
    "Quadriceps": "PMID:34170576,PMID:36662126",
    "Omuz": "PMID:40692697,PMID:33312291",
    "Biceps": "PMID:39809454,PMID:36662126",
    "Baldır": "PMID:38156065,PMID:36662126",
    "Karın": "PMID:18827329,PMID:36662126",
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Yalnızca başlık doğrulaması yapılmış PMID'ler üretim prompt'una girebilir.
# Eski seed dosyasında konu dışı PMID'ler bulunuyordu; bu kapı yeni ve mevcut
# veritabanlarında bunların tekrar kullanılmasını engeller.
VERIFIED_RESEARCH_PMIDS = {
    "PMID:27433992", "PMID:30558493", "PMID:36662126", "PMID:41646176",
    "PMID:35044672", "PMID:28919335", "PMID:28698222", "PMID:36057893",
    "PMID:35873210", "PMID:38274324", "PMID:34560586", "PMID:31482093", "PMID:37914977",
    "PMID:38156065", "PMID:39809454", "PMID:40692697", "PMID:33312291", "PMID:18827329",
}


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _dedupe_food_duplicates(db) -> int:
    """Seed yanlışlığından kalan birebir isim tekrarlarını temizler (id: en küçük kalır)."""
    seen = {}
    removed = 0
    for item in db.query(FoodItem).order_by(FoodItem.id.asc()).all():
        key = _norm(item.name)
        if key in seen:
            db.delete(item)
            removed += 1
        else:
            seen[key] = item
    db.commit()
    return removed


def seed_foods(db) -> int:
    added = 0
    # SQLite lower() ASCII dışı Türkçe karakterleri işlemez -> eşleşmeyi Python'da yap
    existing_names = {_norm(f.name) for f in db.query(FoodItem).all()}
    for record in FOOD_SEED + FOOD_SEED_USDA:
        (name, aliases, category, kcal, prot, carb, fat, fiber, portion, tags) = record
        if _norm(name) in existing_names:
            continue  # idempotent: dokunma
        db.add(FoodItem(
            name=name, aliases=aliases, category=category,
            calories_per_100g=kcal, protein_per_100g=prot, carbs_per_100g=carb, fats_per_100g=fat,
            fiber_per_100g=fiber, typical_portion_g=portion,
            source="local_tr", dietary_tags=tags, pending_review=False,
        ))
        existing_names.add(_norm(name))
        added += 1
    db.commit()
    return added


def seed_exercises(db) -> int:
    added = 0
    existing_items = {_norm(f.name): f for f in db.query(ExerciseLibraryItem).all()}
    existing_names = set(existing_items)
    for record in EXERCISE_SEED:
        (name, aliases, muscle, ex_type, stretch, unilateral, equipment, cue, rep_bias, contra, evidence, reason) = record
        if _norm(name) in existing_names:
            existing = existing_items[_norm(name)]
            existing.evidence_refs = None
            existing.evidence_level = existing.evidence_level or "unverified"
            continue
        # Eski seed PMID'leri hareket-spesifik olarak doğrulanmadı; yanlış
        # atıfları egzersiz kayıtlarına taşımıyoruz.
        db.add(ExerciseLibraryItem(
            name=name, aliases=aliases, muscle_group=muscle, exercise_type=ex_type,
            stretch_mediated=stretch, unilateral=unilateral, equipment=equipment,
            technique_cue=cue, rep_range_bias=rep_bias, contraindications=contra,
            evidence_refs=None, selection_reason=reason, pending_review=False,
        ))
        existing_names.add(_norm(name))
        added += 1
    db.commit()
    return added


def seed_research(db) -> int:
    added = 0
    existing_rows = {_norm(n.title)[:40]: n for n in db.query(ResearchNote).all()}
    existing_titles = set(existing_rows)
    for record in RESEARCH_SEED:
        (topic, title, summary, rule, evidence, target_mg, score) = record
        refs = [ref.strip() for ref in (evidence or "").split(",") if ref.strip()]
        evidence = ",".join(refs) if refs and all(ref in VERIFIED_RESEARCH_PMIDS for ref in refs) else None
        if _norm(title)[:40] in existing_titles:
            existing_rows[_norm(title)[:40]].evidence_refs = evidence
            continue
        db.add(ResearchNote(
            topic=topic, title=title, summary=summary, finding_rule=rule,
            evidence_refs=evidence, source_type="curated",
            target_muscle_group=target_mg, relevance_score=score, is_active=True,
        ))
        existing_titles.add(_norm(title)[:40])
        
        added += 1
    db.commit()
    return added


def seed_evidence_exercises(db) -> int:
    """Kanıta dayalı hipertrofi çekirdeğini egzersiz kütüphanesine yazar (idempotent).
    Kayıt şeması: (name, aliases, muscle_group, exercise_type, stretch, unilateral,
    equipment, cue, rep_bias, contra, muscle_head, stimulus_rating, rom_profile,
    difficulty, force_type, mechanic, goals, selection_reason).
    Kütüphanede zaten var olan kayıtlar üzerine YAZILMAZ - ama boş meta alanları
    (_pick_best) varsa bilgi kazandırılır (kanonik isimle eşleşen ham parquet kayıtları)."""
    added = 0
    enriched = 0
    core_names = {_norm(rec[0]) for rec in EVIDENCE_EXERCISES}
    for rec in EVIDENCE_EXERCISES:
        (name, aliases, muscle, ex_type, stretch, unilateral, equipment, cue,
         rep_bias, contra, muscle_head, stimulus_rating, rom_profile,
         difficulty, force_type, mechanic, goals, selection_reason) = rec
        key = _norm(name)
        matches = db.query(ExerciseLibraryItem).filter(ExerciseLibraryItem.name.ilike(f"%{key}%")).all()
        # Kısmi isim eşleşmesi kullanma: "Cable Lateral Raise" gibi bir
        # kanonik kayıt, "Lean-away Cable Lateral Raise" varyantına yazılmamalı.
        # Aksi halde bazı çekirdek hareketler hiç oluşturulmadan yanlış metadata
        # alıyordu.
        item = next((candidate for candidate in matches if _norm(candidate.name) == key), None)
        if not item:
            item = ExerciseLibraryItem(
                name=name, aliases=aliases or "", muscle_group=muscle,
                exercise_type=ex_type, stretch_mediated=stretch, unilateral=unilateral,
                equipment=equipment or "bodyweight", technique_cue=cue,
                rep_range_bias=rep_bias or None,
                contraindications=contra or "",
                selection_reason=selection_reason, pending_review=False,
                difficulty=difficulty, force_type=force_type, mechanic=mechanic,
                goals=goals, source="local_tr", is_bodyweight=(equipment == "bodyweight"),
                muscle_head=muscle_head, stimulus_rating=float(stimulus_rating),
                rom_profile=rom_profile,
                evidence_level="expert_curated",
                evidence_source="curated_hypertrophy_core",
                evidence_refs=GROUP_EXERCISE_EVIDENCE.get(muscle, GENERAL_EXERCISE_EVIDENCE),
                evidence_scope="muscle_group" if muscle in GROUP_EXERCISE_EVIDENCE else "general_mechanistic",
            )
            db.add(item)
            added += 1
        else:
            # Aynı kanonik hareket eski/ham kayıt olarak zaten varsa, küratörlü
            # çekirdek onu güvenilir kayda yükseltir. Bu kayıt parquet kaynaklı
            # olsa bile artık bu kanonik tanımın editoryal metadata'sı otoritedir.
            item.muscle_head = muscle_head
            item.stimulus_rating = float(stimulus_rating)
            item.rom_profile = rom_profile
            item.difficulty = difficulty or item.difficulty
            item.goals = goals or item.goals
            item.selection_reason = selection_reason or item.selection_reason
            item.pending_review = False
            item.evidence_level = "expert_curated"
            item.evidence_source = "curated_hypertrophy_core"
            item.evidence_refs = GROUP_EXERCISE_EVIDENCE.get(muscle, GENERAL_EXERCISE_EVIDENCE)
            item.evidence_scope = "muscle_group" if muscle in GROUP_EXERCISE_EVIDENCE else "general_mechanistic"
            item.source = "local_tr"
            enriched += 1
    # Önceki sürümlerdeki kısmi isim eşleşmeleri (örn. Cable Face Pull -> Face
    # Pull) eski bir kaydı çekirdeğe yanlışlıkla terfi ettirmiş olabilir. Güncel
    # statik çekirdek tek otoritedir; listede olmayan eski terfileri karantinaya
    # alarak stale approval sızıntısını kapat.
    for item in db.query(ExerciseLibraryItem).filter(
        ExerciseLibraryItem.evidence_source == "curated_hypertrophy_core"
    ).all():
        if _norm(item.name) not in core_names:
            item.pending_review = True
            item.evidence_level = "unverified"
            item.evidence_source = "legacy_core_name_review"
            enriched += 1
    db.commit()
    if added or enriched:
        logger.info("[SEED] Kanıt egzersiz çekirdeği: +%d yeni, +%d zenginleştirildi", added, enriched)
    return added


def seed_evidence_topics(db) -> int:
    """'Neden X yerine Y?' kanıt bankasını yazar (idempotent)."""
    added = 0
    existing_rows = {_norm(t.direct_answer)[:40]: t for t in db.query(EvidenceTopic).all()}
    existing = set(existing_rows)
    for rec in EVIDENCE_TOPICS:
        topic = EvidenceTopic(
            topic=rec["topic"],
            question_keywords=rec.get("question_keywords", ""),
            muscle_group=rec.get("muscle_group"),
            focused_exercises=rec.get("focused_exercises", ""),
            direct_answer=rec["direct_answer"],
            biomechanics=rec.get("biomechanics"),
            # Kaynak sözlüğündeki kanonik alan adı exercise_reccs'tir.
            exercise_recommendations=rec.get("exercise_reccs") or rec.get("exercise_recommendations"),
            key_studies=rec.get("key_studies"),
            source_note=rec.get("source_note"),
            is_active=True,
            priority=rec.get("priority", 5),
        )
        key = _norm(topic.direct_answer)[:40]
        old = existing_rows.get(key)
        if old is None:
            # Direct answer metni editoryal olarak değişebilir; aynı konu + kas
            # grubunu kararlı kimlik kabul ederek mevcut kaydı güncelle.
            candidates = [row for row in db.query(EvidenceTopic).all()
                          if row.topic == topic.topic and row.muscle_group == topic.muscle_group]
            if len(candidates) == 1:
                old = candidates[0]
        if old is not None:
            # Kaynak dosyası kanonik otoritedir: eski yanlış PMID/link/öneri
            # üretim veritabanında kalmamalı. Kullanıcıya ait alan yoktur.
            old.topic = topic.topic
            old.question_keywords = topic.question_keywords
            old.muscle_group = topic.muscle_group
            old.focused_exercises = topic.focused_exercises
            old.direct_answer = topic.direct_answer
            old.biomechanics = topic.biomechanics
            old.exercise_recommendations = topic.exercise_recommendations
            old.key_studies = topic.key_studies
            old.source_note = topic.source_note
            old.is_active = topic.is_active
            old.priority = topic.priority
            continue
        db.add(topic)
        existing.add(_norm(topic.direct_answer)[:40])
        added += 1
    db.commit()
    return added


def seed_all(db=None):
    owns_session = db is None
    db = db or SessionLocal()
    try:
        removed = _dedupe_food_duplicates(db)
        if removed:
            logger.info("[SEED] %d birebir isim tekrarı temizlendi", removed)
        foods = seed_foods(db)
        exercises = seed_exercises(db)
        research = seed_research(db)
        evidence_ex = seed_evidence_exercises(db)
        evidence_topics = seed_evidence_topics(db)
        logger.info("[SEED] Besin: +%d, Egzersiz: +%d, Araştırma: +%d, Kanıt egzersiz: +%d, Kanıt konu: +%d (idempotent)",
                    foods, exercises, research, evidence_ex, evidence_topics)
        return {"foods": foods, "exercises": exercises, "research": research,
                "evidence_exercises": evidence_ex, "evidence_topics": evidence_topics}
    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    # Seed komutu uygulama startup'ından bağımsız da çalıştırılabilir; mevcut
    # SQLite kurulumlarında model kolonları seed sorgusundan önce hazır olmalı.
    migrate_schema()
    seed_all()
