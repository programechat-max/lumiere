"""
Stripe webhook işleyicisi — idempotent (aynı event_id iki kez işlenmez, bkz.
WebhookEvent tablosu) (PROMPT 3)."""
import logging

from sqlalchemy.orm import Session

import billing_service
import models

logger = logging.getLogger(__name__)


def already_processed(db: Session, event_id: str) -> bool:
    return db.query(models.WebhookEvent).filter(models.WebhookEvent.event_id == event_id).first() is not None


def mark_processed(db: Session, event_id: str, event_type: str) -> None:
    db.add(models.WebhookEvent(event_id=event_id, event_type=event_type))
    db.commit()


def _find_user_id_for_customer(db: Session, stripe_customer_id: str):
    sub = db.query(models.Subscription).filter(models.Subscription.stripe_customer_id == stripe_customer_id).first()
    return sub.user_id if sub else None


def handle_event(db: Session, event: dict) -> dict:
    event_id = event.get("id")
    event_type = event.get("type")

    if not event_id:
        return {"status": "ignored", "reason": "missing event id"}
    if already_processed(db, event_id):
        return {"status": "duplicate_ignored"}

    data_object = (event.get("data") or {}).get("object") or {}

    if event_type == "customer.subscription.updated" or event_type == "customer.subscription.created":
        customer_id = data_object.get("customer")
        user_id = _find_user_id_for_customer(db, customer_id)
        if user_id:
            billing_service.sync_from_stripe_subscription(db, user_id, data_object)
    elif event_type == "customer.subscription.deleted":
        billing_service.mark_canceled(db, data_object.get("id"))
    elif event_type == "invoice.payment_failed":
        customer_id = data_object.get("customer")
        user_id = _find_user_id_for_customer(db, customer_id)
        if user_id:
            sub = billing_service.get_or_create_subscription(db, user_id)
            sub.status = "past_due"
            db.commit()
            logger.warning("Ödeme başarısız - user_id=%s, fatura=%s", user_id, data_object.get("id"))
    elif event_type == "invoice.paid" or event_type == "payment_intent.succeeded":
        customer_id = data_object.get("customer")
        user_id = _find_user_id_for_customer(db, customer_id)
        if user_id:
            invoice = models.Invoice(
                user_id=user_id,
                stripe_invoice_id=data_object.get("id"),
                amount_due=(data_object.get("amount_paid") or data_object.get("amount") or 0) / 100.0,
                currency=data_object.get("currency", "usd"),
                status="paid",
                pdf_url=data_object.get("invoice_pdf") or data_object.get("hosted_invoice_url"),
            )
            db.add(invoice)
            db.commit()

    mark_processed(db, event_id, event_type)
    return {"status": "processed", "type": event_type}
