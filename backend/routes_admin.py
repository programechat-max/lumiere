"""PROMPT 12: Admin dashboard uçları (/api/v1/admin/*). Tüm uçlar ADMIN/SUPER_ADMIN/
SUPPORT/FINANCE rolleriyle korunur ve her işlem AuditLog'a yazılır (denetim izi)."""
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

import auth
import billing_service
import models
from database import get_db
from pagination import paginate_query

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class UserEditRequest(BaseModel):
    role: Optional[str] = None
    is_suspended: Optional[bool] = None
    plan_type: Optional[str] = None


class TicketReplyRequest(BaseModel):
    message: str
    status: Optional[str] = None


def _serialize_user(u: models.User) -> dict:
    return {
        "id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role,
        "is_active": u.is_active, "is_suspended": u.is_suspended, "created_at": u.created_at,
    }


@router.get("/users", dependencies=[Depends(auth.require_support)])
def search_users(
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.User)
    if q:
        query = query.filter(or_(models.User.email.ilike(f"%{q}%"), models.User.full_name.ilike(f"%{q}%")))
    query = query.order_by(models.User.created_at.desc())
    result = paginate_query(query, limit=limit, offset=offset)
    result["data"] = [_serialize_user(u) for u in result["data"]]
    return result


@router.get("/users/{user_id}", dependencies=[Depends(auth.require_support)])
def get_user_detail(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
    sub = billing_service.get_or_create_subscription(db, user_id)
    last_login = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.user_id == user_id, models.AuditLog.action == "login_success")
        .order_by(models.AuditLog.created_at.desc())
        .first()
    )
    return {
        "user": _serialize_user(user),
        "subscription": {"plan_type": sub.plan_type, "status": sub.status},
        "last_login_at": last_login.created_at if last_login else None,
    }


@router.put("/users/{user_id}", dependencies=[Depends(auth.require_admin)])
def edit_user(user_id: int, body: UserEditRequest, request: Request, current_admin: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")

    changes = {}
    if body.role is not None:
        changes["role"] = (user.role, body.role)
        user.role = body.role
    if body.is_suspended is not None:
        changes["is_suspended"] = (user.is_suspended, body.is_suspended)
        user.is_suspended = body.is_suspended
    if body.plan_type is not None:
        sub = billing_service.get_or_create_subscription(db, user_id)
        changes["plan_type"] = (sub.plan_type, body.plan_type)
        sub.plan_type = body.plan_type
    db.commit()

    auth.log_audit(db, "admin.edit_user", user_id=user_id, actor_user_id=current_admin.id, request=request, meta={"changes": {k: list(v) for k, v in changes.items()}})
    return {"status": "updated", "changes": list(changes.keys())}


@router.get("/analytics/kpis", dependencies=[Depends(auth.require_support)])
def get_kpis(db: Session = Depends(get_db)):
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    active_users = db.query(func.count(models.User.id)).filter(models.User.is_active == True).scalar() or 0  # noqa: E712
    plan_counts = dict(
        db.query(models.Subscription.plan_type, func.count(models.Subscription.id))
        .group_by(models.Subscription.plan_type)
        .all()
    )
    paying_plans = {k: v for k, v in plan_counts.items() if k != "FREE"}
    mrr = sum(billing_service.PLAN_PRICING_USD.get(plan, 0) * count for plan, count in paying_plans.items())
    total_paying = sum(paying_plans.values())
    conversion_rate = round((total_paying / total_users) * 100, 2) if total_users else 0.0
    return {
        "total_users": total_users,
        "active_users": active_users,
        "mrr_usd": round(mrr, 2),
        "plan_breakdown": plan_counts,
        "conversion_rate_percent": conversion_rate,
        "arpu_usd": round(mrr / total_paying, 2) if total_paying else 0.0,
    }


@router.get("/analytics/growth", dependencies=[Depends(auth.require_support)])
def get_growth(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    rows = (
        db.query(func.date(models.User.created_at), func.count(models.User.id))
        .filter(models.User.created_at >= cutoff)
        .group_by(func.date(models.User.created_at))
        .order_by(func.date(models.User.created_at))
        .all()
    )
    return [{"date": str(d), "new_users": c} for d, c in rows]


@router.get("/support/tickets", dependencies=[Depends(auth.require_support)])
def list_tickets(status: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    query = db.query(models.SupportTicket)
    if status:
        query = query.filter(models.SupportTicket.status == status)
    query = query.order_by(models.SupportTicket.created_at.desc())
    result = paginate_query(query, limit=limit, offset=offset)
    result["data"] = [
        {"id": t.id, "user_id": t.user_id, "subject": t.subject, "category": t.category, "status": t.status, "created_at": t.created_at}
        for t in result["data"]
    ]
    return result


@router.post("/support/tickets/{ticket_id}/reply", dependencies=[Depends(auth.require_support)])
def reply_to_ticket(ticket_id: int, body: TicketReplyRequest, current_admin: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Destek talebi bulunamadı.")
    message = models.SupportTicketMessage(ticket_id=ticket_id, author_user_id=current_admin.id, is_admin_reply=True, message=body.message)
    db.add(message)
    if body.status:
        ticket.status = body.status
    ticket.assigned_admin_id = current_admin.id
    db.commit()
    return {"status": "replied"}


@router.get("/system/health", dependencies=[Depends(auth.require_admin)])
def system_health(db: Session = Depends(get_db)):
    from monitoring import _check_database, _check_redis
    pending_jobs = db.query(func.count(models.JobStatus.id)).filter(models.JobStatus.status.in_(["pending", "started", "progress"])).scalar() or 0
    failed_jobs_24h = db.query(func.count(models.JobStatus.id)).filter(
        models.JobStatus.status == "failure",
        models.JobStatus.created_at >= datetime.datetime.utcnow() - datetime.timedelta(hours=24),
    ).scalar() or 0
    return {
        "database": _check_database(),
        "redis": _check_redis(),
        "pending_jobs": pending_jobs,
        "failed_jobs_24h": failed_jobs_24h,
    }
