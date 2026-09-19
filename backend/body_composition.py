"""Vücut kompozisyonu (InBody benzeri) metrik sözlüğü ve fark değerlendirmesi.

Neden ayrı modül: hem API katmanı (main.py) hem AI prompt'u (ai_core.py) hem de
testler aynı metrik tanımlarını kullanmalı. Arayüzdeki "+%2,3" gibi etiketler ve
kırmızı/yeşil renk kararı burada tek yerden üretilir; frontend sadece gösterir.

Renk kuralı (ürün kararı): rozet rengi YALNIZCA Jarvis'in yorumuna (review.sentiment)
göre belirlenir. Jarvis bir düşüşe "olumlu bakmıyorsa" (örn. kas kaybı) değer azalmış
olsa bile kırmızı görünür. AI yanıtı alınamazsa kural tabanlı yedek değerlendirme
(fallback_sentiment) devreye girer ki arayüz boş/sessiz kalmasın.
"""

# Ölçüm alanları — sıra arayüzdeki gösterim sırasıdır.
# prefer: "lower" | "higher" → Jarvis yorumu yoksa hangi yön iyidir (fallback).
METRIC_GROUPS = (
    {
        "key": "general",
        "label": "Genel",
        "metrics": (
            {"key": "body_fat_percent", "label": "Yağ oranı", "unit": "%", "decimals": 1, "prefer": "lower"},
            {"key": "total_fat_kg", "label": "Toplam yağ", "unit": "kg", "decimals": 1, "prefer": "lower"},
            {"key": "lean_mass_kg", "label": "Yağ dışı", "unit": "kg", "decimals": 1, "prefer": "higher"},
            {"key": "muscle_kg", "label": "Kas", "unit": "kg", "decimals": 1, "prefer": "higher"},
            {"key": "bone_mass_kg", "label": "Kemik", "unit": "kg", "decimals": 1, "prefer": "higher"},
            {"key": "body_water_kg", "label": "Sıvı", "unit": "kg", "decimals": 1, "prefer": "higher"},
        ),
    },
    {
        "key": "segment_fat_percent",
        "label": "Segmentel yağ oranı",
        "metrics": (
            {"key": "right_leg_fat_percent", "label": "Sağ bacak", "unit": "%", "decimals": 1, "prefer": "lower"},
            {"key": "left_leg_fat_percent", "label": "Sol bacak", "unit": "%", "decimals": 1, "prefer": "lower"},
            {"key": "right_arm_fat_percent", "label": "Sağ kol", "unit": "%", "decimals": 1, "prefer": "lower"},
            {"key": "left_arm_fat_percent", "label": "Sol kol", "unit": "%", "decimals": 1, "prefer": "lower"},
            {"key": "trunk_fat_percent", "label": "Gövde", "unit": "%", "decimals": 1, "prefer": "lower"},
        ),
    },
    {
        "key": "segment_muscle_kg",
        "label": "Segmentel kas",
        "metrics": (
            {"key": "right_leg_muscle_kg", "label": "Sağ bacak", "unit": "kg", "decimals": 1, "prefer": "higher"},
            {"key": "left_leg_muscle_kg", "label": "Sol bacak", "unit": "kg", "decimals": 1, "prefer": "higher"},
            {"key": "right_arm_muscle_kg", "label": "Sağ kol", "unit": "kg", "decimals": 1, "prefer": "higher"},
            {"key": "left_arm_muscle_kg", "label": "Sol kol", "unit": "kg", "decimals": 1, "prefer": "higher"},
            {"key": "trunk_muscle_kg", "label": "Gövde", "unit": "kg", "decimals": 1, "prefer": "higher"},
        ),
    },
    {
        "key": "segment_fat_kg",
        "label": "Segmentel yağ",
        "metrics": (
            {"key": "right_leg_fat_kg", "label": "Sağ bacak", "unit": "kg", "decimals": 1, "prefer": "lower"},
            {"key": "left_leg_fat_kg", "label": "Sol bacak", "unit": "kg", "decimals": 1, "prefer": "lower"},
            {"key": "right_arm_fat_kg", "label": "Sağ kol", "unit": "kg", "decimals": 1, "prefer": "lower"},
            {"key": "left_arm_fat_kg", "label": "Sol kol", "unit": "kg", "decimals": 1, "prefer": "lower"},
            {"key": "trunk_fat_kg", "label": "Gövde", "unit": "kg", "decimals": 1, "prefer": "lower"},
        ),
    },
)

# Segment sırası cihaz konvansiyonu; arayüzde görsel yerleşim de buna dayanır.
SEGMENT_KEYS = ("right_leg", "left_leg", "right_arm", "left_arm", "trunk")
SEGMENT_LABELS = {
    "right_leg": "Sağ bacak",
    "left_leg": "Sol bacak",
    "right_arm": "Sağ kol",
    "left_arm": "Sol kol",
    "trunk": "Gövde",
}

# Ölçülebilir tüm alan adları (model kolonlarıyla birebir) — formdan gelen
# bilinmeyen anahtarları elemek için kullanılır.
METRIC_KEYS = tuple(
    m["key"] for group in METRIC_GROUPS for m in group["metrics"]
)

SENTIMENTS = ("positive", "negative", "neutral")

# Anlamlı sayılacak en küçük değişim: cihazın ölçüm gürültüsü (0.1 kg / %0.1)
MIN_DELTA = 0.05


def metric_spec(key: str):
    """Metrik tanımını (birim, ondalık, tercih edilen yön) döndürür."""
    for group in METRIC_GROUPS:
        for metric in group["metrics"]:
            if metric["key"] == key:
                return metric
    return None


def format_delta(value: float, unit: str, decimals: int = 1) -> str:
    """+2,3 kg / -1,4 % / 0 kg biçiminde işaretli etiket üretir."""
    rounded = round(value, decimals)
    if abs(rounded) < 10 ** -decimals / 2:
        return f"0 {unit}".strip()
    sign = "+" if rounded > 0 else "-"
    text = f"{abs(rounded):.{decimals}f}".replace(".", ",")
    return f"{sign}{text} {unit}".strip()


def fallback_sentiment(deltas: list) -> str:
    """Jarvis yorumu alınamadığında kural tabanlı yön değerlendirmesi.

    Yağ azalması ve kas/yağ-dışı artışı olumlu; tersi olumsuz sayılır.
    Birden fazla metrik varsa en belirgin (büyük) değişim kazanan olur.
    """
    score = 0.0
    for delta in deltas:
        spec = metric_spec(delta["key"])
        if spec is None or abs(delta["delta"]) < MIN_DELTA:
            continue
        # Yön normalizasyonu: "iyiye" doğru +1, kötüye doğru -1.
        improving = delta["delta"] < 0 if spec["prefer"] == "lower" else delta["delta"] > 0
        # Yüzde değişimlerde mutlak büyüklük kg'lara göre daha küçük olduğundan
        # ağırlığı göreli büyüklükle (önceki değere oran) ölçekle.
        base = delta.get("previous")
        magnitude = abs(delta["delta"]) / abs(base) if base else 0.05
        score += (1 if improving else -1) * max(magnitude, 0.02)
    if score > 0.02:
        return "positive"
    if score < -0.02:
        return "negative"
    return "neutral"


def compare_records(previous, current) -> list:
    """İki ölçüm kaydı arasındaki metrik farklarını döndürür.

    Her iki kayıtta da değer yoksa metrik listeye hiç girmez (eksik veri
    arayüzde sahte satır oluşturmasın).
    """
    deltas = []
    for group in METRIC_GROUPS:
        for spec in group["metrics"]:
            key = spec["key"]
            new_value = getattr(current, key, None)
            old_value = getattr(previous, key, None) if previous is not None else None
            if new_value is None:
                continue
            delta_value = (new_value - old_value) if old_value is not None else None
            deltas.append({
                "key": key,
                "label": spec["label"],
                "group": group["key"],
                "group_label": group["label"],
                "unit": spec["unit"],
                "decimals": spec["decimals"],
                "prefer": spec["prefer"],
                "current": new_value,
                "previous": old_value,
                "delta": delta_value,
                "delta_label": format_delta(delta_value, spec["unit"], spec["decimals"]) if delta_value is not None else None,
            })
    return deltas


def rule_based_review(deltas: list) -> dict:
    """Jarvis'e ulaşılamadığında üretilen yedek yorum (kaynak: rule)."""
    significant = [d for d in deltas if d["delta"] is not None and abs(d["delta"]) >= MIN_DELTA]
    sentiment = fallback_sentiment(significant)
    if not significant:
        summary = "İlk ölçüm kaydedildi. Sonraki ölçümde değişimleri karşılaştıracağım."
    elif sentiment == "positive":
        summary = "Genel tablo olumlu: yağ tarafı gerilerken kas/yağ dışı kütle korunmuş veya artmış görünüyor."
    elif sentiment == "negative":
        summary = "Bu ölçümde olumsuz sinyaller var — yağ artışı veya kas kaybı dikkat gerektiriyor."
    else:
        summary = "Değişimler ölçüm gürültüsü seviyesinde; mevcut plana devam edilebilir."
    return {
        "sentiment": sentiment,
        "summary": summary,
        "highlights": [f"{d['label']} {d['delta_label']}" for d in significant][:6],
        "source": "rule",
    }


def normalize_review(raw, deltas: list) -> dict:
    """AI'dan dönen yorumu güvenli şemaya indirger; bozuksa kural tabanlıya düşer."""
    if not isinstance(raw, dict):
        return rule_based_review(deltas)
    sentiment = raw.get("sentiment")
    if sentiment not in SENTIMENTS:
        return rule_based_review(deltas)
    highlights = raw.get("highlights")
    if not isinstance(highlights, list):
        highlights = []
    summary = raw.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = rule_based_review(deltas)["summary"]
    return {
        "sentiment": sentiment,
        "summary": summary.strip(),
        "highlights": [str(h) for h in highlights if str(h).strip()][:6],
        "source": "jarvis",
    }


def build_metrics_payload(deltas: list, review: dict) -> list:
    """Arayüz için metrik listesi: rozetin rengi Jarvis'in sentiment'inden gelir.

    Bir değişiklik negatif yorum aldıysa değer azalmış olsa bile rozet kırmızıdır;
    bu yüzden yön (ok) ile renk (tone) ayrı alanlarda taşınır.
    """
    payload = []
    for delta in deltas:
        if delta["delta"] is None:
            tone = "neutral"
            direction = "flat"
        else:
            direction = "up" if delta["delta"] > 0 else "down" if delta["delta"] < 0 else "flat"
            tone = review.get("sentiment", "neutral")
            if tone == "neutral" and abs(delta["delta"]) >= MIN_DELTA:
                # Jarvis nötr dediyse ama değişim gerçekse, metrik bazında kural
                # tabanlı yön kullanılır: arayüz tamamen renksiz kalmasın.
                spec = metric_spec(delta["key"])
                improving = delta["delta"] < 0 if spec and spec["prefer"] == "lower" else delta["delta"] > 0
                tone = "positive" if improving else "negative"
        payload.append({
            **{k: v for k, v in delta.items() if k != "prefer"},
            "direction": direction,
            "tone": tone,
        })
    return payload


def group_payload(metrics: list) -> list:
    """Metrikleri gruplara ayırır (Genel / segmentel yağ oranı / kas / yağ)."""
    by_group = {}
    for metric in metrics:
        by_group.setdefault(metric["group"], []).append(metric)
    return [
        {"key": group["key"], "label": group["label"], "metrics": by_group.get(group["key"], [])}
        for group in METRIC_GROUPS
        if by_group.get(group["key"])
    ]


def segment_payload(record) -> list:
    """5 segment için yağ oranı / kas kg / yağ kg üçlüsünü tek kartta toplar."""
    return [
        {
            "key": key,
            "label": SEGMENT_LABELS[key],
            "fat_percent": getattr(record, f"{key}_fat_percent", None),
            "muscle_kg": getattr(record, f"{key}_muscle_kg", None),
            "fat_kg": getattr(record, f"{key}_fat_kg", None),
        }
        for key in SEGMENT_KEYS
    ]


def has_any_value(payload: dict) -> bool:
    """Formdan gelen payload gerçekten bir ölçüm içeriyor mu?"""
    return any(payload.get(key) is not None for key in METRIC_KEYS)


def extract_metric_values(payload: dict) -> dict:
    """Payload'ta AÇIKÇA gönderilen metrik alanlarını ve opsiyonel notu alır.

    Yalnızca payload'da bulunan anahtarlar döner; eksik alanlar None olarak
    eklenmez. Bu kritik: aynı güne yapılan ikinci (kısmi) giriş upsert ile aynı
    satırı güncellediği için, eksik alanları None yazmak kullanıcının daha önce
    girdiği segmentel değerleri sessizce silerdi. Bilinmeyen anahtarlar elenir
    ki form/API üzerinden gelen fazladan alanlar modele sızmasın.
    """
    values = {key: payload[key] for key in METRIC_KEYS if key in payload}
    if payload.get("note") is not None:
        values["note"] = payload["note"]
    return values


def _serialize_record(record) -> dict:
    """Kaydı şema alanlarıyla birebir sözlüğe çevirir (ORM -> API)."""
    payload = {"id": record.id, "date": record.date, "source": record.source,
               "review": record.review, "created_at": record.created_at}
    payload.update({key: getattr(record, key, None) for key in METRIC_KEYS})
    payload["note"] = record.note
    return payload


def build_summary(records: list) -> dict:
    """Kişisel Bilgiler sayfasının tüm verisini tek sözlükte toplar.

    records kronolojik (eskiden yeniye) sırada beklenir. Hiç kayıt yoksa
    has_data=False döner ve arayüz boş durumu gösterir.
    """
    if not records:
        return {
            "has_data": False, "latest": None, "previous": None,
            "first_record_date": None, "record_count": 0, "review": None,
            "metrics": [], "groups": [], "segments": [], "history": [],
        }

    latest = records[-1]
    previous = records[-2] if len(records) > 1 else None
    review = latest.review if isinstance(latest.review, dict) else rule_based_review(
        compare_records(previous, latest)
    )
    metrics = build_metrics_payload(compare_records(previous, latest), review)
    return {
        "has_data": True,
        "latest": _serialize_record(latest),
        "previous": _serialize_record(previous) if previous is not None else None,
        "first_record_date": records[0].date,
        "record_count": len(records),
        "review": review,
        "metrics": metrics,
        "groups": group_payload(metrics),
        "segments": segment_payload(latest),
        "history": [_serialize_record(record) for record in records],
    }

