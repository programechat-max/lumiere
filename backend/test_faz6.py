"""Faz 6 genişletilmiş veri katmanı testleri.

Kapsam:
- Akıllı egzersiz seçici: kas grubu tam eşleşmesi, ekipman/sakatlık filtreleri,
  "Chest-Supported Row" gibi isim tuzağından kaçınma
- Split planlayıcı: 6 gün PPL determinizmi, MAV set tutarlılığı, doğal dil tespiti
- Türk besin genişletmesi: idempotent seed + resolve
- USDA alaka filtresi: yanlış besin kaymasına karşı (ağ gerekmez)
- Bilimsel sorgu domain tespiti (jarvis_brain)
"""
import pytest
from sqlalchemy.orm import Session

import models
from knowledge.seed_knowledge import seed_all
from knowledge.exercise_selector import select_exercises, format_selected_pool
from knowledge.split_planner import build_split, build_split_from_instruction, format_split_plan, detect_split
from knowledge.food_db import seed_turkish_expansion, resolve_food_name
from knowledge.import_usda_foods import _pick_best_filtered
from knowledge.exercise_audit import audit_exercise_library
from knowledge.evidence_exercises import EVIDENCE_EXERCISES


@pytest.fixture
def seeded_db(db_session: Session):
    seed_all(db_session)
    return db_session


# ============ Egzersiz seçici ============

def test_selector_exact_muscle_group_first(seeded_db: Session):
    """muscle_group tam eşleşmesi olan kayıt varsa isim tuzağı kayıtları girmemeli."""
    chest = [e.name for e in select_exercises(seeded_db, "Göğüs", limit=50)]
    assert not any("Chest-Supported" in n for n in chest)


def test_curated_exercise_core_has_complete_metadata():
    from knowledge.evidence_exercises import EVIDENCE_EXERCISES
    required_groups = {"Göğüs", "Sırt", "Quadriceps", "Hamstring & Glute",
                       "Omuz", "Biceps", "Triceps", "Karın", "Baldır"}
    assert required_groups <= {record[2] for record in EVIDENCE_EXERCISES}
    assert len(EVIDENCE_EXERCISES) >= 50
    for record in EVIDENCE_EXERCISES:
        assert record[0] and record[2] and record[7] and record[10]
        assert record[11] is not None and record[12] in {"full", "lengthened", "shortened", "partial", "isometric"}


def test_selector_equipment_filter(seeded_db: Session):
    items = select_exercises(seeded_db, "Göğüs", equipment=["dumbbell"], limit=20)
    assert items, "dumbbell filtreli göğüs havuzu boş olmamalı"
    allowed = {"dumbbell", "bodyweight", None, ""}
    assert all(e.equipment in allowed for e in items)


def test_selector_injury_filter(seeded_db: Session):
    """Omuz sakatlığı notu içeren kayıtlar (contraindications=shoulder) elenmeli."""
    items = select_exercises(seeded_db, "Göğüs", injury_notes="omuz ağrısı var", limit=50)
    for e in items:
        assert "shoulder" not in (e.contraindications or "")


def test_selector_format_pool_caps_per_group(seeded_db: Session):
    groups = ["Göğüs", "Sırt", "Quadriceps"]
    text = format_selected_pool(seeded_db, groups, per_group=4)
    # gerçek format: her grup bir satır, 'Grup: öğe | öğe | ...'
    lines = [l for l in text.strip().splitlines() if l.strip()]
    assert len(lines) == 3, f"3 grup satırı beklenir, gelen: {lines!r}"
    for line in lines:
        body = line.split(":", 1)[1] if ":" in line else line
        items = [i for i in body.split("|") if i.strip()]
        assert len(items) <= 4, f"per_group=4 aşildi: {line[:80]}"


def test_selector_unknown_group_fallback(seeded_db: Session):
    """Bilinmeyen kas grubu boş döner, hata atmaz."""
    assert select_exercises(seeded_db, "Kanat Olsun", limit=5) == []


# ============ Split planlayıcı ============

def test_split_6_day_ppl_deterministic():
    plan = build_split(6, goal="hypertrophy", level="intermediate")
    assert plan.name == "Push/Pull/Legs (PPL)"
    assert len(plan.days) == 6
    # aynı parametre aynı sonucu vermeli (determinizm)
    plan2 = build_split(6, goal="hypertrophy", level="intermediate")
    assert [d["day_title"] for d in plan.days] == [d["day_title"] for d in plan2.days]
    # PPL'de göğüs günü mutlaka olmalı
    chest_days = [d for d in plan.days if "Göğüs" in d["groups"]]
    assert chest_days, "PPL'de göğüs günü olmalı"


def test_split_3_day_full_body():
    plan = build_split(3, goal="hypertrophy")
    assert "Full Body" in plan.name
    assert len(plan.days) == 3


def test_split_4_day_upper_lower():
    plan = build_split(4)
    assert "Upper/Lower" in plan.name
    assert len(plan.days) == 4


def test_split_mav_sets_cover_all_groups():
    """Her split gününün kas grupları MAV (weekly_sets) tablosunda tanımlı olmalı."""
    for days in (2, 3, 4, 5, 6):
        plan = build_split(days)
        for day in plan.days:
            for g in day["groups"]:
                assert g in plan.weekly_sets, f"{plan.name}: {g} MAV tablosunda yok"


def test_detect_split_natural_language():
    days, tip = detect_split("6 gün ppl istiyorum")
    assert days == 6 and tip == "ppl"
    days2, tip2 = detect_split("haftada 4 gün çalışıyorum")
    assert days2 == 4
    days3, tip3 = detect_split("upper lower olsun")
    assert days3 == 4 and tip3 == "upper_lower"


def test_build_split_from_instruction_priority():
    """Kullanıcı 6 gün PPL derse split PPL olmalı."""
    plan = build_split_from_instruction("6 gün ppl istiyorum kas yapmak için")
    assert plan.name == "Push/Pull/Legs (PPL)"
    assert len(plan.days) == 6


def test_instruction_split_uses_level_and_goal_volume_targets():
    beginner_cut = build_split_from_instruction(
        "4 gün upper lower", goal="cut", level="beginner"
    )
    advanced_bulk = build_split_from_instruction(
        "4 gün upper lower", goal="bulk", level="advanced"
    )
    assert beginner_cut.weekly_sets["Göğüs"] < advanced_bulk.weekly_sets["Göğüs"]


def test_format_split_plan_contains_hard_lock():
    text = format_split_plan(build_split(5))
    assert "SPLIT ŞABLONU" in text
    assert "Kas grupları:" in text


# ============ Türk besin genişletmesi ============
def test_turkish_food_seed_idempotent(seeded_db: Session):
    # paylaşılan dosya test DB'sinde önceki koşulardan kalma kayıtlar olabilir;
    # idempotency ölçümü için önce bu seti temizle
    from knowledge.turkish_foods import TURKISH_FOODS_EXPANSION
    names = {f["name"].lower() for f in TURKISH_FOODS_EXPANSION}
    for f in seeded_db.query(models.FoodItem).all():
        if (f.name or "").lower() in names:
            seeded_db.delete(f)
    seeded_db.commit()
    added1 = seed_turkish_expansion(seeded_db)
    added2 = seed_turkish_expansion(seeded_db)
    assert added1 == len(TURKISH_FOODS_EXPANSION)
    assert added2 == 0
    # toplam besin sayısı ~92 olmalı (42 seed + ~50 kürasyon)
    assert seeded_db.query(models.FoodItem).count() >= 90


def test_turkish_food_resolve(seeded_db: Session):
    seed_turkish_expansion(seeded_db)
    food = resolve_food_name(seeded_db, "cacık", save_unresolved=False)
    assert food is not None
    food2 = resolve_food_name(seeded_db, "kuru fasulye", save_unresolved=False)
    assert food2 is not None


# ============ USDA alaka filtresi (ağ gerektirmez) ============

def test_usda_relevance_filter_prefers_keyword_match():
    hits = [
        {"name": "Wild Rice, Dry, Raw", "category": "Foundation", "fdc_id": 1},
        {"name": "Rice, White, Long-grain, Dry, Raw", "category": "Foundation", "fdc_id": 2},
    ]
    best = _pick_best_filtered(hits, "white rice, dry")
    assert best is not None
    assert "White" in best["name"]
    assert best["match_score"] >= 0.5


def test_usda_relevance_filter_rejects_unrelated():
    hits = [{"name": "Wild Rice, Dry, Raw", "category": "Foundation", "fdc_id": 1}]
    # 'canned tuna in water' sorgusu wild rice kaydına düşmemeli
    assert _pick_best_filtered(hits, "canned tuna in water") is None


def test_usda_relevance_filter_exposes_low_confidence():
    hits = [{"name": "Rice, White", "category": "Foundation", "fdc_id": 1}]
    assert _pick_best_filtered(hits, "white rice dry raw")["match_score"] < 0.8


def test_exercise_audit_separates_production_eligible_records(seeded_db: Session):
    report = audit_exercise_library(seeded_db)
    assert report["total"] >= report["production_eligible"]
    assert report["production_eligible"] > 0
    assert report["quarantined"] == report["total"] - report["production_eligible"]
    assert "expert_curated" in report["evidence_levels"]
    assert report["evidence_levels"].get("unverified", 0) == report["quarantined"]
    assert report["production_eligible"] == len(EVIDENCE_EXERCISES)


def test_food_audit_quarantines_invalid_or_untrusted_records(seeded_db: Session):
    from knowledge.food_audit import audit_food_library
    from knowledge.food_quality import is_food_production_eligible

    invalid = models.FoodItem(
        name="Bozuk besin", category="other", source="ai_added",
        calories_per_100g=100, protein_per_100g=-1, carbs_per_100g=10,
        fats_per_100g=2, pending_review=False,
    )
    seeded_db.add(invalid)
    seeded_db.commit()

    report = audit_food_library(seeded_db)

    assert not is_food_production_eligible(invalid)
    assert report["quarantine_reasons"]["untrusted_source"] >= 1
    assert report["quarantine_reasons"]["negative_macro"] >= 1


def test_exercise_review_requires_metadata_and_records_audit(seeded_db: Session):
    from knowledge.exercise_review import approve_exercise

    item = models.ExerciseLibraryItem(
        name="Review Queue Exercise", muscle_group="Göğüs", equipment="dumbbell",
        exercise_type="secondary_compound", pending_review=True,
        muscle_head="overall", stimulus_rating=7.5, rom_profile="full",
        technique_cue="Kontrollü hareket", selection_reason="Kademeli yüklenebilir.",
        evidence_refs="PMID:36662126",
    )
    seeded_db.add(item)
    seeded_db.commit()

    approved = approve_exercise(seeded_db, item.id, "reviewer-1", "Metadata ve kullanım profili kontrol edildi.")

    assert approved.pending_review is False
    assert approved.evidence_level == "expert_curated"
    assert approved.evidence_source == "manual_review"
    assert approved.reviewed_by == "reviewer-1"
    assert approved.reviewed_at is not None


def test_knowledge_health_check_passes_seeded_layer(seeded_db: Session):
    from knowledge.health_check import run_health_check

    report = run_health_check(seeded_db)

    assert report["ok"] is True
    assert all(check["ok"] for check in report["checks"].values())


def test_volume_landmarks_expose_evidence_scope_and_confidence():
    from knowledge.volume_landmarks import get_volume_targets

    targets = get_volume_targets()
    assert targets["Göğüs"]["evidence_refs"] == "PMID:27433992,PMID:35873210"
    assert targets["Göğüs"]["evidence_scope"] == "general_landmark"
    assert targets["Göğüs"]["evidence_confidence"] == "moderate"


# ============ Bilimsel sorgu domain tespiti ============

def test_detect_query_domain_science():
    from jarvis_brain import _detect_query_domain
    assert _detect_query_domain("Bununla ilgili bir çalışma var mı, kanıt ne diyor?") == "science"
    assert _detect_query_domain("Makale önerir misin, literatürde ne yazıyor?") == "science"


def test_science_words_have_multibyte_tokens():
    """_tokenize Türkçe karakter desteği: 'araştırma' tokeni bulunabilmeli."""
    from jarvis_brain import _tokenize, SCIENCE_WORDS
    tokens = _tokenize("araştırma gösteriyor")
    assert any(t in SCIENCE_WORDS for t in tokens)
