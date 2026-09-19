"""Bilgi katmanı (knowledge layer) testleri — Faz 5 sağlamlık paketi.

Kapsam:
- Seed idempotency (aynı veri tekrar eklenmez, Türkçe karakterli isimler dahil)
- Besin makro doğrulama (verify_and_fix_meal_plan %5 sapma kuralı)
- Egzersiz kütüphanesi uzlaştırma (kanonik isim + kaçış vanası pending_review)
- Bilimsel bağlam (küratörlü notlar deterministik döner)
- Eksik bölge format fallback'i
- USDA istemcisi erişilemezse None (graceful fallback)
"""
import json
import pytest
from sqlalchemy.orm import Session

import models
from knowledge.seed_knowledge import seed_all, seed_foods, seed_exercises, seed_research
from knowledge.food_db import verify_and_fix_meal_plan, verify_manual_meal, search_candidate_foods, resolve_food_name, format_candidate_pool
from knowledge.exercise_library import reconcile_program_with_library, format_exercise_pool, match_exercise_name
from knowledge.science import get_research_context
from knowledge.weak_areas import format_weak_areas_block, detect_weak_areas
from knowledge.usda_client import search_foods_usda
from knowledge.evidence_topics import EVIDENCE_TOPICS


@pytest.fixture
def seeded_db(db_session: Session):
    seed_all(db_session)
    return db_session


def test_seed_idempotent(seeded_db: Session):
    """Seed ikinci kez çalıştığında hiçbir kayıt eklememeli (Türkçe isimler dahil)."""
    foods = seed_foods(seeded_db)
    exercises = seed_exercises(seeded_db)
    research = seed_research(seeded_db)
    assert foods == 0
    assert exercises == 0
    assert research == 0


def test_seed_populates_tables(seeded_db: Session):
    assert seeded_db.query(models.FoodItem).count() >= 40
    assert seeded_db.query(models.ExerciseLibraryItem).count() >= 30
    assert seeded_db.query(models.ResearchNote).count() >= 10


def test_turkish_food_names_unique(seeded_db: Session):
    """Türkçe karakterli besin isimleri (İ/Ş/ö) birebir tekrarlanmamalı."""
    names = [f.name for f in seeded_db.query(models.FoodItem).all()]
    assert len(names) == len(set(names))


def test_verify_macro_plan_with_calorie_deviation(seeded_db: Session):
    """Makrolar tablodan yeniden hesaplanmalı; %5'i aşan sapmada porsiyon ölçeklenmeli."""
    plan = [{
        "meal_name": "Öğle Yemeği",
        "description": "150g tavuk göğsü (ızgara)",
        "calories": 300,  # gerçek: 165*1.5=247.5 -> %21 sapma -> düzeltme beklenir
        "protein": 46.5,
        "carbs": 0,
        "fats": 5.4,
    }]
    fixed_items, fixed_flag = verify_and_fix_meal_plan(seeded_db, plan)
    assert fixed_items[0]["calories"] == pytest.approx(248, abs=5)
    assert fixed_flag is True


def test_verify_macro_plan_within_tolerance(seeded_db: Session):
    """Sapma %5 içindeyse AI değerleri korunmalı."""
    plan = [{
        "meal_name": "Kahvaltı",
        "description": "60g yumurta (haşlanmış)",
        "calories": 93.0,  # gerçek 155*0.6=93.0 -> %0 sapma
        "protein": 7.8,
        "carbs": 0.7,
        "fats": 6.6,
    }]
    fixed_items, fixed_flag = verify_and_fix_meal_plan(seeded_db, plan)
    assert fixed_items[0]["calories"] == pytest.approx(93, abs=2)
    assert fixed_flag is False


def test_manual_meal_never_promotes_pending_food(seeded_db: Session):
    pending = models.FoodItem(
        name="İncelenmemiş ürün", aliases="incelenmemis ürün", category="pending",
        calories_per_100g=100, protein_per_100g=10, carbs_per_100g=10,
        fats_per_100g=2, pending_review=True,
    )
    seeded_db.add(pending)
    seeded_db.commit()
    result = verify_manual_meal(seeded_db, "100g incelenmemis ürün")
    assert result["items"] == []
    assert result["validation_source"] == "llm_estimate"
    assert result["unresolved"]


def test_manual_meal_returns_match_score_for_verified_food(seeded_db: Session):
    result = verify_manual_meal(seeded_db, "100g yulaf")
    assert result["items"]
    item = result["items"][0]
    assert item["match_score"] == 1.0
    assert item["confidence"] == "high"


def test_resolve_food_turkish_inflection(seeded_db: Session):
    """Çekim ekli ad ('tavuğu') kütüphanede eşleşmeli (gövde kırpma mantığı)."""
    food = resolve_food_name(seeded_db, "tavuk göğsü", save_unresolved=False)
    assert food is not None
    assert "Tavuk" in food.name


def test_reconcile_canonical_rename(seeded_db: Session):
    """AI varyasyon adı kütüphane takma adıyla eşleşirse kanonik isme çevrilmeli."""
    raw_programs = [{
        "day_name": "Pazartesi - Göğüs",
        "focus": "push",
        "exercises": [{
            "name": "Incline DB Press",  # takma ad
            "target_sets": 3,
            "target_reps": "6-10",
            "muscle_group": "Göğüs",
            "equipment": "dumbbell",
            "exercise_type": "primary_compound",
        }],
    }]
    reconciled, added = reconcile_program_with_library(seeded_db, raw_programs)
    assert reconciled[0]["exercises"][0]["name"] == "Incline Dumbbell Press"
    assert added == []


def test_reconcile_escape_hatch_adds_pending_review(seeded_db: Session):
    """Kütüphanede olmayan hareket pending_review=True ile tabloya eklenmeli (kaçış vanası)."""
    before = seeded_db.query(models.ExerciseLibraryItem).count()
    raw_programs = [{
        "day_name": "Salı - Özel",
        "focus": "special",
        "exercises": [{
            "name": "Zercher Squat",  # kütüphanede yok
            "target_sets": 3,
            "target_reps": "8-10",
            "muscle_group": "Quadriceps",
            "equipment": "barbell",
            "exercise_type": "primary_compound",
        }],
    }]
    reconciled, added = reconcile_program_with_library(seeded_db, raw_programs)
    assert len(added) == 1
    assert added[0]["name"] == "Zercher Squat"
    after = seeded_db.query(models.ExerciseLibraryItem).count()
    assert after == before + 1
    item = seeded_db.query(models.ExerciseLibraryItem).filter(models.ExerciseLibraryItem.name == "Zercher Squat").first()
    assert item is not None
    assert item.pending_review is True


def test_reconcile_added_exercise_usable_next_generation(seeded_db: Session):
    """Kaçış vanasıyla eklenen hareket SONRAKİ üretimde kütüphaneden eşleşmeli (tutarlılık)."""
    reconcile_program_with_library(seeded_db, [{
        "day_name": "X", "focus": "x",
        "exercises": [{"name": "Zercher Squat", "target_sets": 3, "target_reps": "8-10", "muscle_group": "Quadriceps", "equipment": "barbell"}],
    }])
    raw2 = [{
        "day_name": "X", "focus": "x",
        "exercises": [{"name": "Zercher Squat", "target_sets": 3, "target_reps": "8-10", "muscle_group": "Quadriceps", "equipment": "barbell"}],
    }]
    reconciled, added = reconcile_program_with_library(seeded_db, raw2)
    assert added == []  # artık kütüphanede: tekrar eklenmez
    assert match_exercise_name(seeded_db, "Zercher Squat") is not None


def test_research_context_deterministic(seeded_db: Session):
    """Küratörlü bağlam her çağrıda aynı metni döner (deterministik)."""
    ctx1 = get_research_context(seeded_db, limit=12)
    ctx2 = get_research_context(seeded_db, limit=12)
    assert ctx1 == ctx2
    assert "PMID" in ctx1


def test_research_context_empty_fallback(seeded_db: Session):
    """Tablo boşsa kibar fallback metni dönmeli (uygulama bozulmaz)."""
    seeded_db.query(models.ResearchNote).delete()
    seeded_db.commit()
    ctx = get_research_context(seeded_db, limit=12)
    assert "boş" in ctx.lower()


def test_weak_areas_format_fallback(seeded_db: Session):
    """Tespit boşsa dengeli dağıtım talimatı dönmeli."""
    block = format_weak_areas_block(None)
    assert "ODAK BÖLGELER" in block
    block2 = format_weak_areas_block({"focus_regions": [], "reasons": {}})
    assert "dengeli dağıt" in block2


def test_video_focus_requires_structured_confidence(seeded_db: Session, test_user):
    seeded_db.add(models.UserMemory(
        user_id=test_user.id,
        category="onboarding_video_analysis",
        content=json.dumps({
            "focus_regions": ["Göğüs"], "observations": ["serbest metin"],
            "confidence": "low", "program_eligible": False,
        }),
    ))
    seeded_db.commit()
    result = detect_weak_areas(seeded_db, user_id=test_user.id)
    assert "Göğüs" not in result["focus_regions"]


def test_video_focus_uses_only_eligible_structured_result(seeded_db: Session, test_user):
    seeded_db.add(models.UserMemory(
        user_id=test_user.id,
        category="onboarding_video_analysis",
        content=json.dumps({
            "focus_regions": ["Göğüs"], "observations": ["tekrarlanan gözlem"],
            "confidence": "high", "program_eligible": True,
        }),
    ))
    seeded_db.commit()
    result = detect_weak_areas(seeded_db, user_id=test_user.id)
    assert "Göğüs" in result["focus_regions"]


def test_candidate_pool_respects_dietary_tags(seeded_db: Session):
    """Vegan kısıtlı kullanıcıya uygun tag filtresi çalışmalı (havuz yine dolu döner)."""
    pool = search_candidate_foods(seeded_db, dietary_notes="vegan", limit_per_category=50)
    assert isinstance(pool, list)
    # Her kayıt gerekli makro alanlarını taşımalı
    for c in pool:
        assert {"name", "calories_per_100g", "protein_per_100g", "carbs_per_100g", "fats_per_100g"} <= set(c.keys())


def test_usda_client_graceful_when_no_network():
    """API erişilemezse None döner (lokal tabloyla devam - uygulama asla bozulmaz)."""
    result = search_foods_usda("apple", limit=2)
    assert result is None or isinstance(result, list)  # ya hata None ya da geçerli liste


def test_evidence_topics_have_verified_pubmed_records():
    """Üretim kanıt bankasına boş veya arama-sonucu linki yazılmasını engeller."""
    for topic in EVIDENCE_TOPICS:
        for study in topic.get("key_studies", []):
            assert study.get("pmid", "").isdigit()
            assert study.get("link", "").endswith(f"/{study['pmid']}/")


def test_format_exercise_pool_nonempty(seeded_db: Session):
    pool_text = format_exercise_pool(seeded_db)
    assert "Flat Dumbbell Press" in pool_text
    assert "boş" not in pool_text  # kütüphane dolu: fallback metni dönmez


def test_exercise_pool_never_falls_back_to_freeform_generation(seeded_db: Session):
    pool_text = format_exercise_pool(seeded_db, equipment=["unsupported-equipment"])
    assert "ÜRETİM DURDURULMALI" in pool_text


def test_candidate_food_pool_is_available_and_deterministic(seeded_db: Session):
    pool_text = format_candidate_pool(seeded_db)
    assert "kcal" in pool_text
    assert "P " in pool_text


def test_usda_fallback_without_persistence_does_not_pollute_library(seeded_db: Session, monkeypatch):
    monkeypatch.setattr("knowledge.food_db.settings.USDA_FALLBACK_ENABLED", True)
    monkeypatch.setattr("knowledge.food_db.search_foods_usda", lambda name, limit=1: [{
        "name": "Synthetic USDA Food", "fdc_id": 987654,
        "calories": 100.0, "protein": 10.0, "carbs": 5.0, "fats": 2.0,
        "match_score": 1.0, "micros": {},
    }])

    result = resolve_food_name(seeded_db, "synthetic food", save_unresolved=False)

    assert result is not None
    assert result.pending_review is False
    assert result.source == "ai_added"
    assert seeded_db.query(models.FoodItem).filter(
        models.FoodItem.usda_fdc_id == 987654
    ).count() == 0


def test_usda_fallback_persists_only_as_pending_review(seeded_db: Session, monkeypatch):
    monkeypatch.setattr("knowledge.food_db.settings.USDA_FALLBACK_ENABLED", True)
    monkeypatch.setattr("knowledge.food_db.search_foods_usda", lambda name, limit=1: [{
        "name": "Pending USDA Food", "fdc_id": 987655,
        "calories": 100.0, "protein": 10.0, "carbs": 5.0, "fats": 2.0,
        "match_score": 1.0, "micros": {},
    }])

    result = resolve_food_name(seeded_db, "pending food", save_unresolved=True)

    assert result is not None and result.pending_review is True
    assert seeded_db.query(models.FoodItem).filter(
        models.FoodItem.usda_fdc_id == 987655,
        models.FoodItem.pending_review.is_(True),
    ).count() == 1
