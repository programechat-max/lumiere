"""PROMPT 3: Abonelik & faturalandırma uçları (/api/v1/billing/*)."""
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth
import billing_service
import models
import stripe_client
import webhook_handler
from database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class SubscribeRequest(BaseModel):
    plan_type: str  # PREMIUM_MONTHLY | PREMIUM_ANNUAL | COACHING


def _require_stripe():
    if not stripe_client.settings.stripe_configured:
        raise HTTPException(status_code=503, detail="Faturalandırma sistemi henüz yapılandırılmadı (Stripe anahtarları eksik).")


@router.get("/plans")
def get_available_plans():
    """Tüm üyelik planlarını (FREE, PRO, ELITE, ELITE_PLUS) ve karşılaştırmalarını döner."""
    return {
        "plans": billing_service.PLAN_DETAILS,
        "pricing_try": billing_service.PLAN_PRICING_TRY,
        "pricing_usd": billing_service.PLAN_PRICING_USD,
        "features": billing_service.FEATURE_MATRIX,
    }


@router.get("/subscription")
def get_subscription(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    sub = billing_service.get_or_create_subscription(db, current_user.id)
    return {
        "plan_type": sub.plan_type,
        "status": sub.status,
        "trial_end": sub.trial_end,
        "current_period_start": sub.current_period_start,
        "current_period_end": sub.current_period_end,
        "cancel_at": sub.cancel_at,
        "features": billing_service.FEATURE_MATRIX.get(sub.plan_type, billing_service.FEATURE_MATRIX["FREE"]),
        "pricing": billing_service.PLAN_PRICING_USD,
        "pricing_try": billing_service.PLAN_PRICING_TRY,
        "available_plans": billing_service.PLAN_DETAILS,
    }


@router.post("/change-plan")
def change_or_renew_plan(body: SubscribeRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Kullanıcının planını anında yükseltir, düşürür veya yeniler."""
    plan_upper = body.plan_type.upper().strip()
    if plan_upper not in billing_service.FEATURE_MATRIX:
        raise HTTPException(status_code=400, detail="Geçersiz plan tipi. (FREE, PRO, ELITE, ELITE_PLUS)")
    sub = billing_service.upgrade_or_renew_plan(db, current_user.id, plan_upper)
    return {
        "status": "success",
        "plan_type": sub.plan_type,
        "current_period_end": sub.current_period_end,
        "message": f"Üyeliğiniz başarıyla {billing_service.FEATURE_MATRIX.get(sub.plan_type, {}).get('name', sub.plan_type)} paketine güncellendi."
    }


@router.post("/subscribe")
def subscribe(body: SubscribeRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    plan_upper = body.plan_type.upper().strip()
    if plan_upper not in billing_service.FEATURE_MATRIX:
        raise HTTPException(status_code=400, detail="Geçersiz plan tipi.")
    if not billing_service.is_trial_eligible(db, current_user.id):
        # Deneme bittiyse bile doğrudan plan değişimini sağla
        sub = billing_service.upgrade_or_renew_plan(db, current_user.id, plan_upper)
        return {"status": "plan_updated", "plan_type": sub.plan_type, "trial_end": sub.trial_end}
    sub = billing_service.start_trial(db, current_user.id, plan_upper)
    return {"status": "trial_started", "trial_end": sub.trial_end}


@router.post("/checkout")
def create_checkout(body: SubscribeRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    _require_stripe()
    sub = billing_service.get_or_create_subscription(db, current_user.id)
    if not sub.stripe_customer_id:
        sub.stripe_customer_id = stripe_client.create_customer(current_user.email, current_user.full_name, metadata={"user_id": current_user.id})
        db.commit()
    try:
        checkout_url = stripe_client.create_checkout_session(
            sub.stripe_customer_id, body.plan_type,
            success_url=f"{FRONTEND_URL}/billing/success", cancel_url=f"{FRONTEND_URL}/billing/cancel",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"checkout_url": checkout_url}


@router.post("/manage")
def manage_billing(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    _require_stripe()
    sub = billing_service.get_or_create_subscription(db, current_user.id)
    if not sub.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Bu kullanıcı için henüz bir Stripe müşteri kaydı yok.")
    portal_url = stripe_client.create_billing_portal_session(sub.stripe_customer_id, return_url=f"{FRONTEND_URL}/billing")
    return {"portal_url": portal_url}


@router.get("/invoices")
def list_invoices(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    invoices = (
        db.query(models.Invoice)
        .filter(models.Invoice.user_id == current_user.id)
        .order_by(models.Invoice.created_at.desc())
        .all()
    )
    return [
        {"id": i.id, "amount_due": float(i.amount_due or 0), "currency": i.currency, "status": i.status,
         "pdf_url": i.pdf_url, "created_at": i.created_at}
        for i in invoices
    ]


@router.post("/cancel")
def cancel_subscription(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    sub = billing_service.get_or_create_subscription(db, current_user.id)
    if sub.stripe_subscription_id and stripe_client.settings.stripe_configured:
        stripe_client.cancel_subscription(sub.stripe_subscription_id, at_period_end=True)
    sub.status = "canceled"
    db.commit()
    return {"status": "cancel_scheduled"}


@router.get("/usage")
def get_usage(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    import datetime
    month_start = datetime.date.today().replace(day=1)
    meal_plans_this_month = (
        db.query(models.MealPlanItem)
        .filter(models.MealPlanItem.user_id == current_user.id, models.MealPlanItem.created_at >= month_start)
        .count()
    )
    sub = billing_service.get_or_create_subscription(db, current_user.id)
    limit = billing_service.FEATURE_MATRIX.get(sub.plan_type, {}).get("meal_plans_per_month")
    return {"meal_plans_used": meal_plans_this_month, "meal_plans_limit": limit}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe imza doğrulaması yapılan, idempotent webhook alıcısı."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe_client.construct_webhook_event(payload, sig_header)
    except stripe_client.StripeNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.warning("Stripe webhook imza doğrulaması başarısız: %s", exc)
        raise HTTPException(status_code=400, detail="Geçersiz webhook imzası.")

    result = webhook_handler.handle_event(db, event if isinstance(event, dict) else event.to_dict())
    return result
