"""Split planlayıcı — gün sayısı + hedef + deneyime göre bilimsel, MAV-yönlü
bir haftalık antrenman iskeleti kurar (Faz 6).

Kullanıcı "6 gün PPL" derse; AI'ya bırakmak yerine programatik şablon üretir:
  - Gün sayısı + hedef -> en uygun split tipi (PPL / Upper-Lower / Full-Body / Arnold)
  - Her güne kas grubu kümesi + birincil kas grubu (focus) atanır
  - MAV hacim dağılımı (weak_areas MUSCLE_WEIGHTS ile uyumlu) prompt'a girer
  - Agonist/antagonist dengesi (PPL'de push-pull-legs ayrımı) korunur

AI iskelete hareket doldurur; şablondan çıkamaz -> "saçma split" senaryosu önlenir.
"""
from __future__ import annotations

from dataclasses import dataclass, field

PPL_TEMPLATE = [
    {"day_title": "Push A", "focus": "Göğüs", "groups": ["Göğüs", "Omuz", "Triceps"]},
    {"day_title": "Pull A", "focus": "Sırt", "groups": ["Sırt", "Biceps"]},
    {"day_title": "Legs A", "focus": "Quadriceps", "groups": ["Quadriceps", "Hamstring & Glute", "Baldır", "Karın"]},
    {"day_title": "Push B", "focus": "Omuz", "groups": ["Göğüs", "Omuz", "Triceps"]},
    {"day_title": "Pull B", "focus": "Sırt", "groups": ["Sırt", "Biceps", "Karın"]},
    {"day_title": "Legs B", "focus": "Hamstring & Glute", "groups": ["Quadriceps", "Hamstring & Glute", "Baldır"]},
]

UPPER_LOWER_TEMPLATE = [
    {"day_title": "Upper A", "focus": "Göğüs", "groups": ["Göğüs", "Sırt", "Omuz", "Biceps", "Triceps"]},
    {"day_title": "Lower A", "focus": "Quadriceps", "groups": ["Quadriceps", "Hamstring & Glute", "Baldır", "Karın"]},
    {"day_title": "Upper B", "focus": "Sırt", "groups": ["Göğüs", "Sırt", "Omuz", "Biceps", "Triceps"]},
    {"day_title": "Lower B", "focus": "Hamstring & Glute", "groups": ["Quadriceps", "Hamstring & Glute", "Baldır"]},
]

FULL_BODY_3 = [
    {"day_title": "Full Body A", "focus": "Göğüs", "groups": ["Göğüs", "Sırt", "Quadriceps", "Karın"]},
    {"day_title": "Full Body B", "focus": "Sırt", "groups": ["Sırt", "Omuz", "Hamstring & Glute"]},
    {"day_title": "Full Body C", "focus": "Quadriceps", "groups": ["Göğüs", "Quadriceps", "Biceps", "Triceps"]},
]

FULL_BODY_2 = [
    {"day_title": "Full Body A", "focus": "Göğüs", "groups": ["Göğüs", "Sırt", "Quadriceps", "Karın"]},
    {"day_title": "Full Body B", "focus": "Sırt", "groups": ["Sırt", "Omuz", "Hamstring & Glute"]},
]

ARNOLD_TEMPLATE = [
    {"day_title": "Göğüs + Sırt", "focus": "Göğüs", "groups": ["Göğüs", "Sırt", "Karın"]},
    {"day_title": "Omuz + Kol", "focus": "Omuz", "groups": ["Omuz", "Biceps", "Triceps"]},
    {"day_title": "Bacak + Karın", "focus": "Quadriceps", "groups": ["Quadriceps", "Hamstring & Glute", "Baldır", "Karın"]},
    {"day_title": "Göğüs + Sırt", "focus": "Sırt", "groups": ["Göğüs", "Sırt", "Karın"]},
    {"day_title": "Omuz + Kol", "focus": "Triceps", "groups": ["Omuz", "Biceps", "Triceps"]},
    {"day_title": "Bacak", "focus": "Hamstring & Glute", "groups": ["Quadriceps", "Hamstring & Glute", "Baldır"]},
]


@dataclass
class SplitPlan:
    name: str
    days: list = field(default_factory=list)
    day_count: int = 0
    weekly_sets: dict = field(default_factory=dict)
    explanation: str = ""


# Kas grubu başına MAV hedefi (set) — hacim dağılımı için taban.
# FAZ 7: artık volume_landmarks modülünden (kanıta dayalı, seviye/hedef ölçekli) gelir;
# bu sözlük yalnızca fallback'tir (seviye/hedef parametresi verilmezse kullanılır).
MAV_SETS = {
    "Göğüs": 14, "Sırt": 16, "Quadriceps": 16, "Hamstring & Glute": 14,
    "Omuz": 12, "Biceps": 10, "Triceps": 10, "Karın": 8, "Baldır": 8,
}


def _weekly_sets_for(level: str = "intermediate", goal: str = "hypertrophy") -> dict:
    """Kanıta dayalı per-kas MAV dağılımını döndürür (volume_landmarks)."""
    try:
        from knowledge.volume_landmarks import get_volume_targets
        targets = get_volume_targets(level=level, goal=goal)
        return {muscle: t["MAV"] for muscle, t in targets.items()}
    except Exception:
        return dict(MAV_SETS)
def build_split(gun_sayisi: int, goal: str = "hypertrophy", level: str = "intermediate") -> SplitPlan:
    """Gün sayısına en uygun şablonu seçer; gerekirse 4/5 gün çeşitlemeleri kurar."""
    days = max(2, min(7, gun_sayisi or 4))

    if days == 2:
        template = FULL_BODY_2
        name = "Full Body (2 gün)"
    elif days == 3:
        template = FULL_BODY_3
        name = "Full Body (3 gün)"
    elif days == 4:
        template = UPPER_LOWER_TEMPLATE if level != "beginner" else FULL_BODY_3 + [FULL_BODY_3[0]]
        name = "Upper/Lower (4 gün)" if level != "beginner" else "Full Body x4"
    elif days == 5:
        template = UPPER_LOWER_TEMPLATE + [UPPER_LOWER_TEMPLATE[0]]
        name = "Upper/Lower + üst (5 gün)"
    elif days >= 6:
        template = PPL_TEMPLATE + ([PPL_TEMPLATE[0]] if days >= 7 else [])
        name = "Push/Pull/Legs (PPL)" if days == 6 else "Push/Pull/Legs + Push"

    plan_days = template[:days]

    # FAZ 7: kanıta dayalı per-kas MAV hedefleri (seviye + hedef ölçekli)
    weekly = _weekly_sets_for(level=level, goal=goal)

    explanation = (
        f"Split: {name}. Hacim kas gruplarına toparlanabilir birden fazla oturuma bölünür; "
        f"oturum başına aynı kasa 8 set üstüne taşınmaz ve uygun hareketlerde uzun kas "
        f"pozisyonu değerlendirilir. Frekans, toplam hacim ve toparlanmaya göre ayarlanır."
    )

    return SplitPlan(
        name=name,
        days=[dict(d) for d in plan_days],
        day_count=len(plan_days),
        weekly_sets=weekly,
        explanation=explanation,
    )


def format_split_plan(plan: SplitPlan) -> str:
    """Split iskeletini AI prompt'una girecek metne çevirir."""
    lines = [
        "═══ SPLIT ŞABLONU (KESİN - BU İSKELETE HAREKET DOLDUR, ŞABLONDAN ÇIKMA) ═══",
        f"Split tipi: {plan.name}",
        f"Haftalık set hedefi per kas grubu: " + ", ".join(
            f"{k}={v}" for k, v in plan.weekly_sets.items()
        ),
        "Günler:",
    ]
    for i, day in enumerate(plan.days, 1):
        lines.append(
            f"- Gün {i}: {day['day_title']} | ODAK: {day['focus']} | Kas grupları: {', '.join(day['groups'])}"
        )
    lines.append(plan.explanation)
    return "\n".join(lines)


# Kullanıcı metninden gün sayısı + istenen split tipini kaba sezme
def detect_split(instruction: str, default_days: int = 4) -> tuple[int, str]:
    """'6 gün' / 'ppl' / 'upper lower' / 'full body' / 'arnold' gibi istekleri çözer."""
    import re
    text = (instruction or "").lower()
    days = None
    m = re.search(r"(\d+)\s*(?:gün|gun|günde|gunluk)", text)
    if m:
        days = int(m.group(1))
    tip = ""
    if "ppl" in text or "push pull leg" in text or "push/pull/leg" in text:
        tip = "ppl"
    elif "arnold" in text:
        tip = "arnold"
    elif "upper lower" in text or "upper/lower" in text or "üst alt" in text:
        tip = "upper_lower"
    elif "full body" in text or "tam vücut" in text or "fullbody" in text:
        tip = "full_body"
    return (days or default_days, tip)


def build_split_from_instruction(instruction: str, goal: str = "hypertrophy",
                                 level: str = "intermediate", default_days: int = 4) -> SplitPlan:
    """Kullanıcı talimatından split tipi/gün sayısı sezer; şablonu kurar."""
    days, tip = detect_split(instruction, default_days)
    weekly = _weekly_sets_for(level=level, goal=goal)
    if tip == "ppl":
        if days < 3:
            days = 3
        return SplitPlan("Push/Pull/Legs (PPL)", [dict(d) for d in PPL_TEMPLATE[:days]],
                         day_count=min(days, 6), weekly_sets=weekly,
                         explanation="PPL: hacim kas gruplarına birden fazla oturuma bölünür; frekans toplam hacim ve toparlanmaya göre ayarlanır.")
    if tip == "arnold":
        return SplitPlan("Arnold Split (6 gün)", [dict(d) for d in ARNOLD_TEMPLATE],
                         day_count=len(ARNOLD_TEMPLATE), weekly_sets=weekly,
                         explanation="Arnold split: göğüs+sırt ve omuz+kol antogonist ikililerle kurulur.")
    if tip == "upper_lower":
        return SplitPlan("Upper/Lower", [dict(d) for d in UPPER_LOWER_TEMPLATE[:days]],
                         day_count=min(days, 6), weekly_sets=weekly,
                         explanation="Upper/Lower: üst-alt hacmi toparlanabilir oturumlara bölünür; frekans katı üstünlük değil planlama aracıdır.")
    if tip == "full_body":
        return SplitPlan("Full Body", [dict(d) for d in FULL_BODY_3[:days]],
                         day_count=min(days, 6), weekly_sets=weekly,
                         explanation="Full body: tüm kas grupları her oturumda temas eder, hacim düşük tutulur.")
    return build_split(days, goal, level)
