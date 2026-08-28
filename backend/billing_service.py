"""
Abonelik iş mantığı: plan/özellik matrisi, deneme süresi uygunluğu, feature-gating
(PROMPT 3). Stripe hesabı yapılandırılmamışsa tüm kullanıcılar FREE planında kabul
edilir ve sadece FREE özellik setine erişebilir - uygulama asla çökmez."""
import datetime
from typing import Optional

from sqlalchemy.orm import Session

import models
from config import settings

# Plan başına özellik matrisi — 4 Üyelik Seviyesi: FREE, PRO, ELITE, ELITE_PLUS
FEATURE_MATRIX = {
    "FREE": {
        "name": "Free (Ücretsiz)",
        "ai_chat": False,
        "meal_plans_per_month": 1,
        "workout_ai_generation": False,
        "food_photo_analysis": True,
        "form_analysis": False,
        "coaching": False,
        "daily_limit_multiplier": 1,
    },
    "PRO": {
        "name": "Pro",
        "ai_chat": True,
        "meal_plans_per_month": None,
        "workout_ai_generation": True,
        "food_photo_analysis": True,
        "form_analysis": True,
        "coaching": False,
        "daily_limit_multiplier": 5,
    },
    "ELITE": {
        "name": "Elite (Elit)",
        "ai_chat": True,
        "meal_plans_per_month": None,
        "workout_ai_generation": True,
        "food_photo_analysis": True,
        "form_analysis": True,
        "coaching": True,
        "daily_limit_multiplier": 10,
    },
    "ELITE_PLUS": {
        "name": "Elite+ (Elit+)",
        "ai_chat": True,
        "meal_plans_per_month": None,
        "workout_ai_generation": True,
        "food_photo_analysis": True,
        "form_analysis": True,
        "coaching": True,
        "priority_support": True,
        "daily_limit_multiplier": 99,
    },
    # Geriye dönük uyumluluk takma adları
    "PREMIUM_MONTHLY": {
        "name": "Pro",
        "ai_chat": True,
        "meal_plans_per_month": None,
        "workout_ai_generation": True,
        "food_photo_analysis": True,
        "form_analysis": True,
        "coaching": False,
        "daily_limit_multiplier": 5,
    },
    "PREMIUM_ANNUAL": {
        "name": "Elite",
        "ai_chat": True,
        "meal_plans_per_month": None,
        "workout_ai_generation": True,
        "food_photo_analysis": True,
        "form_analysis": True,
        "coaching": True,
        "daily_limit_multiplier": 10,
    },
    "COACHING": {
        "name": "Elite+",
        "ai_chat": True,
        "meal_plans_per_month": None,
        "workout_ai_generation": True,
        "food_photo_analysis": True,
        "form_analysis": True,
        "coaching": True,
        "priority_support": True,
        "daily_limit_multiplier": 99,
    },
}

PLAN_PRICING_USD = {
    "FREE": 0.0,
    "PRO": 9.99,
    "ELITE": 19.99,
    "ELITE_PLUS": 39.99,
    "PREMIUM_MONTHLY": 9.99,
    "PREMIUM_ANNUAL": 19.99,
    "COACHING": 39.99,
}

PLAN_PRICING_TRY = {
    "FREE": 0,
    "PRO": 299,
    "ELITE": 599,
    "ELITE_PLUS": 999,
}

PLAN_DETAILS = [
    {
        "id": "FREE",
        "name": "Free",
        "badge": "Başlangıç",
        "price_try": 0,
        "price_usd": 0,
        "period": "Süresiz",
        "popular": False,
        "description": "Temel fitness ve beslenme takibi için ideal.",
        "features": [
            "Temel Antrenman ve Beslenme Günlüğü",
            "Standart Kalori ve Makro Hesaplama",
            "Aylık 1 Adet Yapay Zeka Planı",
            "Sınırlı Fotoğraftan Yemek Analizi",
            "Topluluk Desteği",
        ],
        "limits": "Günde 5 işlem"
    },
    {
        "id": "PRO",
        "name": "Pro",
        "badge": "En Çok Tercih Edilen",
        "price_try": 299,
        "price_usd": 9.99,
        "period": "aylık",
        "popular": True,
        "description": "Akıllı yapay zeka koçu ile hedeflerine hızlı ulaş.",
        "features": [
            "Jarvis AI Koç ile 7/24 Kesintisiz Sohbet",
            "Sınırsız Fotoğraftan Kalori & Makro Analizi",
            "Sınırsız Kişiselleştirilmiş Antrenman & Diyet Planı",
            "Haftalık Otomatik Gelişim Raporları",
            "Gelişmiş Makro & Kilo Takip Grafikleri",
        ],
        "limits": "Günde 50 AI işlemi"
    },
    {
        "id": "ELITE",
        "name": "Elite",
        "badge": "Gelişmiş Sporcu",
        "price_try": 599,
        "price_usd": 19.99,
        "period": "aylık",
        "popular": False,
        "description": "Form ve postür analiziyle maksimum hipertrofi.",
        "features": [
            "Pro'daki Tüm Özellikler Dahil",
            "Fotoğraf ve Videodan AI Hareket Form Analizi",
            "Postür, Simetri & Kas Gelişim Değerlendirmesi",
            "Anlık RPE ve Ağırlık Artış Progresyon Motoru",
            "Kas Isı Haritası & Akıllı Deload Yönetimi",
        ],
        "limits": "Günde 150 AI işlemi"
    },
    {
        "id": "ELITE_PLUS",
        "name": "Elite+",
        "badge": "VIP / Pro Koçluk",
        "price_try": 999,
        "price_usd": 39.99,
        "period": "aylık",
        "popular": False,
        "description": "En üst düzey VIP deneyim ve öncelikli AI işlemci gücü.",
        "features": [
            "Elite'deki Tüm Özellikler Dahil",
            "7/24 Öncelikli Ultra Hızlı Jarvis Core Yanıtları",
            "Birebir Sesli Check-in & Sesli Koçluk Analitiği",
            "VIP Beslenme/Mikro-Makro Hassas Optimizasyonu",
            "Özel Egzersiz Değişim & Sakatlık Önleme Motoru",
            "Öncelikli VIP Destek Hattı",
        ],
        "limits": "Sınırsız AI işlemi"
    }
]


def get_or_create_subscription(db: Session, user_id: int) -> models.Subscription:
    sub = db.query(models.Subscription).filter(models.Subscription.user_id == user_id).first()
    if not sub:
        sub = models.Subscription(user_id=user_id, plan_type="FREE", status="active")
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


def is_trial_eligible(db: Session, user_id: int) -> bool:
    """Kullanıcı hiç deneme süresi kullanmadıysa uygundur (tek seferlik 7 gün)."""
    sub = get_or_create_subscription(db, user_id)
    return sub.trial_end is None and sub.plan_type == "FREE"


def start_trial(db: Session, user_id: int, plan_type: str) -> models.Subscription:
    sub = get_or_create_subscription(db, user_id)
    now = datetime.datetime.utcnow()
    sub.plan_type = plan_type
    sub.status = "trialing"
    sub.trial_end = now + datetime.timedelta(days=settings.TRIAL_PERIOD_DAYS)
    sub.current_period_start = now
    sub.current_period_end = sub.trial_end
    db.commit()
    db.refresh(sub)
    return sub


def has_feature_access(subscription: Optional[models.Subscription], feature: str) -> bool:
    plan = (subscription.plan_type if subscription else "FREE") or "FREE"
    status = (subscription.status if subscription else "active") or "active"
    if status in ("canceled", "unpaid", "past_due"):
        plan = "FREE"
    return bool(FEATURE_MATRIX.get(plan, FEATURE_MATRIX["FREE"]).get(feature, False))


def sync_from_stripe_subscription(db: Session, user_id: int, stripe_sub: dict) -> models.Subscription:
    """Stripe webhook'undan gelen abonelik verisiyle yerel kaydı senkronize eder."""
    sub = get_or_create_subscription(db, user_id)
    sub.stripe_subscription_id = stripe_sub.get("id")
    sub.status = stripe_sub.get("status", sub.status)
    price_id = None
    items = (stripe_sub.get("items") or {}).get("data") or []
    if items:
        price_id = items[0].get("price", {}).get("id")
    for plan_name, price_getter in {
        "PREMIUM_MONTHLY": settings.STRIPE_PRICE_PREMIUM_MONTHLY,
        "PREMIUM_ANNUAL": settings.STRIPE_PRICE_PREMIUM_ANNUAL,
        "COACHING": settings.STRIPE_PRICE_COACHING,
    }.items():
        if price_id and price_id == price_getter:
            sub.plan_type = plan_name
    if stripe_sub.get("current_period_start"):
        sub.current_period_start = datetime.datetime.utcfromtimestamp(stripe_sub["current_period_start"])
    if stripe_sub.get("current_period_end"):
        sub.current_period_end = datetime.datetime.utcfromtimestamp(stripe_sub["current_period_end"])
    if stripe_sub.get("cancel_at"):
        sub.cancel_at = datetime.datetime.utcfromtimestamp(stripe_sub["cancel_at"])
    db.commit()
    db.refresh(sub)
    return sub


def upgrade_or_renew_plan(db: Session, user_id: int, plan_type: str, duration_days: int = 30) -> models.Subscription:
    """Kullanıcının planını doğrudan yükseltir veya yeniler."""
    sub = get_or_create_subscription(db, user_id)
    now = datetime.datetime.utcnow()
    sub.plan_type = plan_type
    sub.status = "active"
    sub.current_period_start = now
    sub.current_period_end = now + datetime.timedelta(days=duration_days)
    sub.cancel_at = None
    db.commit()
    db.refresh(sub)
    return sub


def mark_canceled(db: Session, stripe_subscription_id: str) -> Optional[models.Subscription]:
    sub = db.query(models.Subscription).filter(models.Subscription.stripe_subscription_id == stripe_subscription_id).first()
    if sub:
        sub.status = "canceled"
        sub.plan_type = "FREE"
        db.commit()
    return sub

