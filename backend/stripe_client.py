"""
Stripe API sarmalayıcısı (PROMPT 3). STRIPE_SECRET_KEY tanımlı değilse tüm
fonksiyonlar StripeNotConfiguredError fırlatır - böylece Stripe hesabı olmayan
bir geliştirme ortamında uygulama çökmeden "faturalandırma yapılandırılmamış"
hatası döner."""
import logging
from typing import Optional

import stripe

from config import settings

logger = logging.getLogger(__name__)

PLAN_PRICE_MAP = {
    "PREMIUM_MONTHLY": lambda: settings.STRIPE_PRICE_PREMIUM_MONTHLY,
    "PREMIUM_ANNUAL": lambda: settings.STRIPE_PRICE_PREMIUM_ANNUAL,
    "COACHING": lambda: settings.STRIPE_PRICE_COACHING,
}


class StripeNotConfiguredError(Exception):
    pass


def _ensure_configured():
    if not settings.stripe_configured:
        raise StripeNotConfiguredError("Stripe henüz yapılandırılmadı (STRIPE_SECRET_KEY eksik).")
    stripe.api_key = settings.STRIPE_SECRET_KEY


def create_customer(email: str, name: str, metadata: Optional[dict] = None) -> str:
    _ensure_configured()
    customer = stripe.Customer.create(email=email, name=name, metadata=metadata or {})
    return customer.id


def create_checkout_session(customer_id: str, plan_type: str, success_url: str, cancel_url: str) -> str:
    _ensure_configured()
    price_id = PLAN_PRICE_MAP.get(plan_type, lambda: None)()
    if not price_id:
        raise ValueError(f"'{plan_type}' planı için Stripe fiyat ID'si yapılandırılmamış.")
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        subscription_data={"trial_period_days": settings.TRIAL_PERIOD_DAYS},
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session.url


def create_billing_portal_session(customer_id: str, return_url: str) -> str:
    _ensure_configured()
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url


def cancel_subscription(stripe_subscription_id: str, at_period_end: bool = True) -> dict:
    _ensure_configured()
    if at_period_end:
        return stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=True)
    return stripe.Subscription.delete(stripe_subscription_id)


def list_invoices(customer_id: str, limit: int = 20):
    _ensure_configured()
    return stripe.Invoice.list(customer=customer_id, limit=limit)


def construct_webhook_event(payload: bytes, sig_header: str):
    """İmza doğrulaması yaparak Stripe webhook olayını güvenli şekilde çözer."""
    _ensure_configured()
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise StripeNotConfiguredError("STRIPE_WEBHOOK_SECRET tanımlı değil - webhook imzası doğrulanamaz.")
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
