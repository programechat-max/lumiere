"""Vücut kompozisyonu (Kişisel Bilgiler sayfası) testleri.

Kapsam:
- İlk ölçümün "ilk kayıt tarihi"ni belirlemesi ve boş durumun doğru raporlanması
- Opsiyonel alanların hepsinin birden çalışması; hiç değer girilmemişse 422
- Aynı gün ikinci girişin yeni satır açmak yerine günü güncellemesi (upsert)
- Değişim etiketleri (+/- %, +/- kg) ve Jarvis kaynaklı renk tonu (tone)
- Kas kaybı gibi "düşüş ama kötü" durumun negatif yorumlanması
- Onboarding "Vücut Analizi" adımının ilk ölçümü kalıcı yazması
- build_system_prompt'un tüm ölçüm verisini Jarvis'e taşıması
"""
from datetime import date, timedelta

import pytest

import ai_core
import body_composition as bc
import crud
import schemas


@pytest.fixture(autouse=True)
def _ai_unavailable(monkeypatch):
    """Testlerde gerçek AI çağrısı yapılmaz.

    Bu dosya Jarvis yorumunun İKİ yolunu da doğrular; ağ çağrısı testi yavaş,
    sonucu ise oynak yapardı (aynı ölçüm için farklı yorum dönebilir). Client
    None olduğunda evaluate_body_composition kural tabanlı yedeğe düşer ve
    arayüz sözleşmesi (delta_label / direction / tone) deterministik kalır.
    """
    monkeypatch.setattr(ai_core, "_genai_client", None)


def _general_payload(**overrides) -> dict:
    """Genel + segmentel alanları dolu örnek ölçüm (InBody çıktısı gibi)."""
    payload = {
        "body_fat_percent": 22.4, "total_fat_kg": 18.2, "lean_mass_kg": 63.0,
        "muscle_kg": 34.5, "bone_mass_kg": 3.2, "body_water_kg": 41.0,
        "right_leg_fat_percent": 24.1, "left_leg_fat_percent": 23.6,
        "right_arm_fat_percent": 18.9, "left_arm_fat_percent": 19.4,
        "trunk_fat_percent": 26.3,
        "right_leg_muscle_kg": 9.8, "left_leg_muscle_kg": 9.7,
        "right_arm_muscle_kg": 3.4, "left_arm_muscle_kg": 3.3,
        "trunk_muscle_kg": 26.1,
        "right_leg_fat_kg": 3.2, "left_leg_fat_kg": 3.1,
        "right_arm_fat_kg": 0.8, "left_arm_fat_kg": 0.8,
        "trunk_fat_kg": 10.4,
    }
    payload.update(overrides)
    return payload


def _past(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def test_empty_state_reports_no_data(client, auth_headers):
    res = client.get("/api/body-composition", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["has_data"] is False
    assert body["record_count"] == 0
    assert body["first_record_date"] is None
    assert body["metrics"] == []


def test_requires_authentication(client):
    assert client.get("/api/body-composition").status_code == 401


def test_empty_payload_is_rejected(client, auth_headers):
    """Hiçbir alan doldurulmadıysa boş kayıt açılmamalı."""
    assert client.post("/api/body-composition", headers=auth_headers, json={}).status_code == 422


def test_first_measurement_becomes_first_record_date(client, auth_headers):
    res = client.post("/api/body-composition", headers=auth_headers, json=_general_payload())
    assert res.status_code == 200
    body = res.json()
    assert body["has_data"] is True
    assert body["record_count"] == 1
    assert body["first_record_date"] == date.today().isoformat()
    assert body["latest"]["body_fat_percent"] == 22.4
    # İlk ölçümde karşılaştırılacak veri yok → nötr başlangıç yorumu.
    assert body["review"]["sentiment"] == "neutral"
    assert body["metrics"][0]["delta_label"] is None


def test_partial_measurement_is_accepted(client, auth_headers):
    """Kullanıcı yalnızca yağ oranını okuyabildiyse sadece o alan kaydedilir."""
    res = client.post("/api/body-composition", headers=auth_headers, json={"body_fat_percent": 21.0})
    assert res.status_code == 200
    body = res.json()
    assert [m["key"] for m in body["metrics"]] == ["body_fat_percent"]
    assert body["latest"]["muscle_kg"] is None


def test_same_day_second_entry_updates_instead_of_duplicating(client, auth_headers):
    client.post("/api/body-composition", headers=auth_headers, json={"body_fat_percent": 22.4})
    res = client.post("/api/body-composition", headers=auth_headers, json={"body_fat_percent": 21.8})
    assert res.status_code == 200
    body = res.json()
    assert body["record_count"] == 1
    assert body["latest"]["body_fat_percent"] == 21.8


def test_same_day_partial_entry_preserves_other_fields(client, auth_headers):
    """Aynı güne kısmi giriş, girilmeyen alanları SİLMEMELİ.

    Regresyon: upsert aynı satırı güncellediği için, payload'da olmayan alanların
    None olarak yazılması kullanıcının daha önce girdiği tüm segmentel değerleri
    sessizce siliyordu (Kişisel Bilgiler sayfası boşalıyordu).
    """
    client.post("/api/body-composition", headers=auth_headers, json=_general_payload())
    res = client.post(
        "/api/body-composition", headers=auth_headers,
        json={"body_fat_percent": 21.0, "muscle_kg": 35.0},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["record_count"] == 1
    assert body["latest"]["body_fat_percent"] == 21.0
    assert body["latest"]["muscle_kg"] == 35.0
    # Dokunulmayan alanlar korunur
    assert body["latest"]["bone_mass_kg"] == 3.2
    assert body["latest"]["trunk_fat_percent"] == 26.3
    assert body["latest"]["right_arm_muscle_kg"] == 3.4
    assert [m["key"] for m in body["metrics"] if m["group"] == "general"] == [
        "body_fat_percent", "total_fat_kg", "lean_mass_kg", "muscle_kg", "bone_mass_kg", "body_water_kg",
    ]


def test_same_day_correction_compares_against_earlier_measurement(client, auth_headers):
    """Aynı gün düzeltmesi, karşılaştırma bazını sıfırlamamalı.

    Baz aynı günün satırı olsaydı tüm değişimler '0' görünür ve kullanıcı bugün
    yaptığı düzeltmede gerçek ilerlemeyi kaybederdi.
    """
    client.post(
        "/api/body-composition", headers=auth_headers,
        json={**_general_payload(), "date": _past(7)},
    )
    client.post("/api/body-composition", headers=auth_headers, json={**_general_payload(), "body_fat_percent": 21.4})
    res = client.post(
        "/api/body-composition", headers=auth_headers,
        json={"body_fat_percent": 20.9, "muscle_kg": 35.2},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["record_count"] == 2  # bugünün kaydı tek satır kaldı
    by_key = {m["key"]: m for m in body["metrics"]}
    # Baz 7 gün önceki ölçüm: yağ 22.4 → 20.9
    assert by_key["body_fat_percent"]["previous"] == 22.4
    assert by_key["body_fat_percent"]["delta_label"] == "-1,5 %"
    assert by_key["body_fat_percent"]["direction"] == "down"
    assert by_key["body_fat_percent"]["tone"] == "positive"


def test_metric_values_reject_impossible_input(client, auth_headers):
    assert client.post(
        "/api/body-composition", headers=auth_headers, json={"body_fat_percent": 220}
    ).status_code == 422


def test_segments_cover_all_five_regions(client, auth_headers):
    res = client.post("/api/body-composition", headers=auth_headers, json=_general_payload())
    segments = res.json()["segments"]
    assert [s["key"] for s in segments] == list(bc.SEGMENT_KEYS)
    trunk = next(s for s in segments if s["key"] == "trunk")
    assert trunk["label"] == "Gövde"
    assert trunk["fat_percent"] == 26.3
    assert trunk["muscle_kg"] == 26.1
    assert trunk["fat_kg"] == 10.4
def test_change_labels_and_tones_follow_jarvis_review(client, auth_headers):
    """Yağ düşüşü + kas artışı → pozitif yorum, yeşil rozet, işaretli etiketler."""
    client.post(
        "/api/body-composition", headers=auth_headers,
        json={**_general_payload(), "date": _past(7)},
    )
    improved = _general_payload(
        body_fat_percent=20.1, total_fat_kg=16.0, muscle_kg=35.6, trunk_muscle_kg=26.9,
    )
    res = client.post("/api/body-composition", headers=auth_headers, json=improved)
    assert res.status_code == 200
    body = res.json()
    assert body["review"]["sentiment"] == "positive"
    by_key = {m["key"]: m for m in body["metrics"]}
    assert by_key["body_fat_percent"]["delta_label"] == "-2,3 %"
    assert by_key["body_fat_percent"]["direction"] == "down"
    assert by_key["body_fat_percent"]["tone"] == "positive"
    assert by_key["muscle_kg"]["delta_label"] == "+1,1 kg"
    assert by_key["muscle_kg"]["direction"] == "up"
    assert by_key["muscle_kg"]["tone"] == "positive"
    # Karşılaştırmanın dayanağı da döner: arayüz "önceki ölçüm" satırını bundan gösterir.
    assert body["previous"]["body_fat_percent"] == 22.4
    assert body["previous"]["date"] == _past(7)


def test_muscle_loss_is_reviewed_negative(client, auth_headers):
    """Kas kaybı bir düşüştür ama iyi değildir: Jarvis yorumu negatif olmalı."""
    client.post(
        "/api/body-composition", headers=auth_headers,
        json={**_general_payload(), "date": _past(7)},
    )
    res = client.post(
        "/api/body-composition", headers=auth_headers,
        json=_general_payload(body_fat_percent=23.5, muscle_kg=31.0, trunk_muscle_kg=23.4),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["review"]["sentiment"] == "negative"
    by_key = {m["key"]: m for m in body["metrics"]}
    assert by_key["muscle_kg"]["direction"] == "down"
    # Düşüş olmasına rağmen renk negatif: rozet rengi yalnızca Jarvis'ten gelir.
    assert by_key["muscle_kg"]["tone"] == "negative"


def test_history_is_returned_chronologically(db_session, client, test_user, auth_headers):
    """Haftalık karşılaştırma tablosu eskiden yeniye sıralı seri bekler."""
    for day, fat in ((date(2026, 8, 1), 24.0), (date(2026, 8, 8), 22.5), (date(2026, 8, 15), 21.0)):
        crud.create_body_composition(
            db_session,
            schemas.BodyCompositionCreate(body_fat_percent=fat, date=day),
            user_id=test_user.id,
        )
    body = client.get("/api/body-composition", headers=auth_headers).json()
    assert [h["date"] for h in body["history"]] == ["2026-08-01", "2026-08-08", "2026-08-15"]
    assert body["first_record_date"] == "2026-08-01"
    assert body["latest"]["body_fat_percent"] == 21.0
# ============ Onboarding entegrasyonu ============

def test_onboarding_saves_first_measurement(client, auth_headers):
    """Profil oluşturmadaki 'Vücut Analizi' adımı kalıcı ilk kaydı yazar."""
    payload = {
        "goal": "recomp", "current_weight": 78.0, "onboarding_completed": True,
        "body_composition": {"body_fat_percent": 23.1, "muscle_kg": 34.0},
    }
    assert client.post("/api/onboarding/complete", headers=auth_headers, json=payload).status_code == 200
    summary = client.get("/api/body-composition", headers=auth_headers).json()
    assert summary["has_data"] is True
    assert summary["record_count"] == 1
    assert summary["latest"]["body_fat_percent"] == 23.1


def test_onboarding_without_measurement_creates_no_record(client, auth_headers):
    res = client.post(
        "/api/onboarding/complete", headers=auth_headers,
        json={"goal": "recomp", "current_weight": 78.0, "onboarding_completed": True},
    )
    assert res.status_code == 200
    assert client.get("/api/body-composition", headers=auth_headers).json()["has_data"] is False


# ============ Jarvis entegrasyonu ============

def test_system_prompt_carries_full_composition(db_session, client, test_user, auth_headers):
    """Jarvis tüm genel + segmentel değerleri prompt'ta görmeli."""
    client.post("/api/body-composition", headers=auth_headers, json=_general_payload())
    prompt = ai_core.build_system_prompt(db_session, user_id=test_user.id)
    assert "VÜCUT KOMPOZİSYONU" in prompt
    assert "Yağ oranı: 22.4 %" in prompt
    assert "Sağ bacak" in prompt and "Gövde" in prompt
    assert "Segmentel kas" in prompt


def test_fallback_review_used_when_ai_unavailable(db_session, test_user):
    """AI yapılandırılmamışsa kural tabanlı yedek yorum devreye girer ve kayda yazılır."""
    first = crud.create_body_composition(
        db_session,
        schemas.BodyCompositionCreate(body_fat_percent=25.0, date=date(2026, 8, 1)),
        user_id=test_user.id,
    )
    record = crud.create_body_composition(
        db_session,
        schemas.BodyCompositionCreate(body_fat_percent=23.0, date=date(2026, 8, 8)),
        user_id=test_user.id,
    )
    review = ai_core.evaluate_body_composition(db_session, record=record, previous=first, user_id=test_user.id)
    assert review["source"] == "rule"
    assert review["sentiment"] == "positive"
    db_session.refresh(record)
    assert record.review["sentiment"] == "positive"
    assert "Yağ oranı -2,0 %" in record.review["highlights"]