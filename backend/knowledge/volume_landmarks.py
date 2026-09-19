"""
HACİM LANDMARKLARI (FAZ 7) - kanıta dayalı per-kas hipertrofi hacim tablosu.
============================================================================
Kas grubu başına haftalık MEV (Minimum Effective Volume), MAV (Maximum
Adaptive Volume), MRV (Maximum Recoverable Volume), hedef frekans ve RIR
başlangıcını tanımlar. Kaynak: direnç antrenmanı hacim literatürü (Schoenfeld
2017 meta, Israetel/JP hacim landmark'ları, Nunes 2020) + kas boyutu/frekans
kabullenmeleri. AI'ya giden prompt "MAV = X set" hedefini buradan alır;
kullanıcının gün sayısı/deneyimi bu tabloyu ölçekler.

- MAV (set/hafta): büyük kaslar yüksek, küçük kaslar düşük.
- Frekans: kas içi bölünme önerisi (energy sistemine göre).
- RIR_başlangıç: setin başlangıç yakınlığı (failure'a).
"""
from __future__ import annotations

# Hacim landmark'ları evrensel biyolojik eşikler değildir; literatür + pratik
# koçluk verisinden türetilen başlangıç hipotezleridir. Referans kapsamı bu
# yüzden açıkça genel/landmark olarak tutulur, kas-spesifik RCT gibi sunulmaz.
VOLUME_EVIDENCE = {
    "refs": "PMID:27433992,PMID:35873210",
    "scope": "general_landmark",
    "confidence": "moderate",
}

# Bölgesel kas grupları -> bilimsel landmark setleri
VOLUME_LANDMARKS: dict[str, dict] = {
    "Göğüs": {"MEV": 8, "MAV": 14, "MRV": 20, "freq": 2, "rir_init": 2, "comp_priority": "compound+stretch", "required_heads": ("upper", "overall")},
    "Sırt": {"MEV": 10, "MAV": 16, "MRV": 22, "freq": 2, "rir_init": 2, "comp_priority": "compound+stretch", "required_heads": ("lat", "mid_back")},
    "Quadriceps": {"MEV": 8, "MAV": 16, "MRV": 22, "freq": 2, "rir_init": 2, "comp_priority": "compound+stretch", "required_heads": ("overall",)},
    "Hamstring & Glute": {"MEV": 8, "MAV": 14, "MRV": 20, "freq": 2, "rir_init": 2, "comp_priority": "stretch+compound", "required_heads": ("biceps_femoris", "gluteus_maximus")},
    "Omuz": {"MEV": 6, "MAV": 12, "MRV": 18, "freq": 2, "rir_init": 2, "comp_priority": "stretch+compound", "required_heads": ("anterior", "lateral", "posterior")},
    "Biceps": {"MEV": 5, "MAV": 10, "MRV": 15, "freq": 2, "rir_init": 1, "comp_priority": "stretch+shortened", "required_heads": ("long_head", "short_head")},
    "Triceps": {"MEV": 5, "MAV": 10, "MRV": 15, "freq": 2, "rir_init": 1, "comp_priority": "stretch+shortened", "required_heads": ("long_head", "lateral_head", "medial_head")},
    "Karın": {"MEV": 4, "MAV": 8, "MRV": 12, "freq": 3, "rir_init": 1, "comp_priority": "stretch+isometric", "required_heads": ("overall",)},
    "Baldır": {"MEV": 4, "MAV": 8, "MRV": 14, "freq": 3, "rir_init": 1, "comp_priority": "lengthened-isolation", "required_heads": ("gastrocnemius", "soleus")},
}

# Deneyim düzeyi -> MAV ölçek çarpanı (beginner rekabet kapasitesi düşük)
LEVEL_MAV_MULT = {"beginner": 0.75, "intermediate": 1.0, "advanced": 1.1}

# Hedef -> set çarpanı (bulk: hafif fazla, cut: hafif az, strength: yoğunluk için düşük hacim)
GOAL_SET_MULT = {"bulk": 1.1, "cut": 0.9, "recomp": 1.0, "maintain": 1.0, "strength": 0.8, "güç": 0.8}


def get_volume_targets(level: str = "intermediate", goal: str = "recomp") -> dict[str, dict]:
    """Deneyim + hedefe göre ÖLÇEKLENMİŞ per-kas hacim hedeflerini döndürür.
    {kas: {"MEV":.., "MAV":.., "MRV":.., "freq":.., "rir_init":..}}
    MAV, seviye ve hedefe göre ölçeklenir; MEV/MRV referans olarak korunur."""
    mult = LEVEL_MAV_MULT.get(level, 1.0) * GOAL_SET_MULT.get(goal, 1.0)
    out = {}
    for muscle, lm in VOLUME_LANDMARKS.items():
        out[muscle] = {
            "MEV": lm["MEV"],
            "MAV": max(lm["MEV"] + 1, round(lm["MAV"] * mult)),
            "MRV": lm["MRV"],
            "freq": lm["freq"],
            "rir_init": lm["rir_init"],
            "comp_priority": lm["comp_priority"],
            "required_heads": lm.get("required_heads", ()),
            "evidence_refs": lm.get("evidence_refs", VOLUME_EVIDENCE["refs"]),
            "evidence_scope": lm.get("evidence_scope", VOLUME_EVIDENCE["scope"]),
            "evidence_confidence": lm.get("evidence_confidence", VOLUME_EVIDENCE["confidence"]),
        }
    return out


def format_volume_landmarks(level: str = "intermediate", goal: str = "recomp",
                            focus_group: str | None = None, focus_multiplier: float = 1.0) -> str:
    """Prompt'a girecek MAV hedef tablosunu üretir."""
    targets = get_volume_targets(level, goal)
    lines = ["═══ HAFTALIK HACİM HEDEFLERİ (KAS GRUBU BAŞINA - KANITA DAYALI) ═══"]
    for muscle, t in targets.items():
        focus_note = ""
        if focus_group and focus_group.lower() in ("genel", "genel vücut", "full"):
            pass
        elif focus_group and focus_group == muscle:
            focus_note = f"  ★ODAK ★ (x{focus_multiplier:.1f})"
        lines.append(
            f"- {muscle}: MEV={t['MEV']} | MAV={t['MAV']}{focus_note} | MRV={t['MRV']} | "
            f"frekans={t['freq']}x/hafta | RIR başlangıcı={t['rir_init']} | "
            f"güven={t['evidence_confidence']}"
        )
    lines.append("Kurallar: oturum başına aynı kasa 8 seti aşma (PMID:30558493); frekansı"
                 " hacmi kaliteli oturumlara bölmek için kullan, ancak hacim eşitken 2x'in"
                 " 1x'e kesin üstün olduğunu varsayma (PMID:30558493).")
    return "\n".join(lines)
