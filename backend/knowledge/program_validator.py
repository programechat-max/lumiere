"""AI tarafından üretilen program için deterministik güvenlik/kalite kapısı.

Prompt kuralları talimat değil, bu modülün raporladığı gerçek ölçümlerdir.
Validator klinik uygunluk iddia etmez; yalnızca programın bilgi katmanı
kurallarını ihlal edip etmediğini kontrol eder.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re

from knowledge.volume_landmarks import get_volume_targets


def validate_program(programs: list[dict], db=None, level: str = "intermediate",
                     goal: str = "recomp", focus_group: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    weekly = Counter()
    effective_weekly = Counter()
    by_day = defaultdict(Counter)
    frequency = Counter()
    stretch_by_muscle = Counter()
    heads_by_muscle = defaultdict(set)
    seen_names = Counter()
    targets = get_volume_targets(level, goal)

    if not programs:
        errors.append("Program en az bir antrenman günü içermeli.")

    for day in programs or []:
        day_name = day.get("day_name", "Gün")
        if not (day.get("exercises") or []):
            errors.append(f"{day_name}: antrenman günü boş olamaz.")
        touched = set()
        for ex in day.get("exercises", []) or []:
            name = str(ex.get("name") or "").strip()
            muscle = str(ex.get("muscle_group") or "").strip()
            sets = ex.get("target_sets")
            try:
                sets = int(sets)
            except (TypeError, ValueError):
                errors.append(f"{day_name}: {name or 'isimsiz hareket'} set sayısı geçersiz.")
                continue
            if not name or sets < 1 or sets > 8:
                errors.append(f"{day_name}: {name or 'isimsiz hareket'} 1-8 set aralığında olmalı.")
            reps = str(ex.get("target_reps") or "")
            if not re.search(r"\d+\s*(?:-|–|to)\s*\d+", reps, re.I):
                warnings.append(f"{day_name}: {name} tekrar aralığı okunamadı ({reps or 'boş'}).")
            if muscle not in targets:
                errors.append(f"{day_name}: {name} bilinmeyen kas grubuna bağlı ({muscle or 'boş'}).")
                continue
            weekly[muscle] += sets
            by_day[day_name][muscle] += sets
            touched.add(muscle)
            seen_names[name] += 1
            if db is not None:
                from knowledge.exercise_library import match_exercise_name
                item = match_exercise_name(db, name)
                if item is None or item.pending_review or item.evidence_level != "expert_curated":
                    errors.append(f"{day_name}: {name} kanonik/onaylı kütüphanede değil.")
                elif item.muscle_group != muscle:
                    errors.append(
                        f"{day_name}: {name} kas grubu uyuşmuyor; "
                        f"beyan={muscle}, kütüphane={item.muscle_group}."
                    )
                elif item.stretch_mediated:
                    stretch_by_muscle[muscle] += 1
                for head in (item.muscle_head or "").split("|"):
                    if head.strip():
                        heads_by_muscle[muscle].add(head.strip())
                # Bileşik hareketlerin ikincil kas yükünü yarım set olarak
                # say; aynı kası farklı günlerde fark etmeden aşırı yüklemeyi
                # engellerken doğrudan setleri ayrıca raporla.
                for secondary in (item.secondary_muscles or "").split(","):
                    secondary = secondary.strip().lower()
                    for group, keywords in {
                        "Göğüs": ("chest", "pectoral", "göğüs"),
                        "Sırt": ("back", "lat", "rhomboid", "trapezius", "sırt"),
                        "Omuz": ("shoulder", "deltoid", "omuz"),
                        "Biceps": ("biceps", "brachialis"),
                        "Triceps": ("triceps",),
                        "Quadriceps": ("quad", "quadriceps"),
                        "Hamstring & Glute": ("hamstring", "glute"),
                    }.items():
                        if any(keyword in secondary for keyword in keywords):
                            effective_weekly[group] += sets * 0.5
                            break
            elif ex.get("stretch_mediated"):
                stretch_by_muscle[muscle] += 1
        for muscle in touched:
            frequency[muscle] += 1

    for day_name, counts in by_day.items():
        for muscle, sets in counts.items():
            if sets > 8:
                errors.append(f"{day_name}: {muscle} için {sets} set var; günlük üst sınır 8.")

    for muscle, total in weekly.items():
        target = targets.get(muscle)
        if target and total > target["MRV"]:
            errors.append(f"{muscle}: haftalık {total} set MRV {target['MRV']} üstünde.")
        if target and total < target["MEV"]:
            warnings.append(f"{muscle}: haftalık {total} set MEV {target['MEV']} altında.")
        if target and frequency[muscle] < min(2, target["freq"]):
            warnings.append(f"{muscle}: haftalık temas {frequency[muscle]}x; öneri {target['freq']}x.")
        if total >= target["MEV"] and not stretch_by_muscle[muscle]:
            warnings.append(f"{muscle}: programda tam-germe profilli hareket görünmüyor.")
        if db is not None and target:
            observed = "|".join(heads_by_muscle[muscle])
            missing_heads = [head for head in target.get("required_heads", ())
                             if head not in observed]
            if total >= target["MEV"] and missing_heads:
                warnings.append(f"{muscle}: kas başı kapsaması eksik ({', '.join(missing_heads)}).")

    for muscle, indirect in effective_weekly.items():
        target = targets.get(muscle)
        if target and weekly[muscle] + indirect > target["MRV"]:
            warnings.append(
                f"{muscle}: dolaylı setlerle tahmini efektif hacim "
                f"{weekly[muscle] + indirect:.1f}; MRV {target['MRV']} üstü."
            )

    repeated = {name: count for name, count in seen_names.items() if count > 2}
    for name, count in repeated.items():
        errors.append(f"{name}: haftada {count} kez tekrarlandı; aynı hareket en fazla 2 kez.")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "weekly_sets": dict(weekly),
        "effective_weekly_sets": {k: round(v, 1) for k, v in effective_weekly.items()},
        "frequency": dict(frequency),
        "duplicate_exercises": repeated,
        "head_coverage": {muscle: sorted(heads) for muscle, heads in heads_by_muscle.items()},
        "focus_group": focus_group,
    }


def validate_split_compliance(programs: list[dict], split_days: list[dict]) -> dict:
    """Üretilen programın deterministik split iskeletinden sapmasını raporlar.

    Split planner yalnızca prompt bağlamı olmamalı: gün sayısı ve her günün
    kapsadığı kas grupları burada tekrar ölçülür. Kas grubu eksikliği hata,
    isim/odak metni farklılığı ise uyarı olarak raporlanır.
    """
    errors: list[str] = []
    warnings: list[str] = []
    actual_days = list(programs or [])
    expected_days = list(split_days or [])
    if len(actual_days) != len(expected_days):
        errors.append(f"Split gün sayısı uyuşmuyor: beklenen {len(expected_days)}, üretilen {len(actual_days)}.")

    for index, expected in enumerate(expected_days[:len(actual_days)]):
        actual = actual_days[index]
        day_label = actual.get("day_name") or f"Gün {index + 1}"
        expected_groups = set(expected.get("groups") or [])
        actual_groups = {
            str(ex.get("muscle_group") or "").strip()
            for ex in (actual.get("exercises") or [])
            if str(ex.get("muscle_group") or "").strip()
        }
        missing = sorted(expected_groups - actual_groups)
        extra = sorted(actual_groups - expected_groups)
        if missing:
            errors.append(f"{day_label}: split kas grupları eksik ({', '.join(missing)}).")
        if extra:
            errors.append(f"{day_label}: splitte olmayan ek kas grupları var ({', '.join(extra)}).")
        expected_title = str(expected.get("day_title") or "").strip().lower()
        actual_title = str(actual.get("day_name") or "").strip().lower()
        if expected_title and expected_title not in actual_title:
            warnings.append(f"Gün {index + 1}: beklenen ad '{expected.get('day_title')}', üretilen '{actual.get('day_name', '')}'.")

    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "expected_days": len(expected_days), "actual_days": len(actual_days)}


def assert_split_compliance(programs: list[dict], split_days: list[dict]) -> dict:
    report = validate_split_compliance(programs, split_days)
    if not report["valid"]:
        raise ValueError("Program split iskeletinden geçemedi: " + " | ".join(report["errors"]))
    return report


def assert_valid_program(*args, **kwargs) -> dict:
    report = validate_program(*args, **kwargs)
    if not report["valid"]:
        raise ValueError("Program bilgi katmanı doğrulamasından geçmedi: " + " | ".join(report["errors"]))
    return report
