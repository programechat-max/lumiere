"""PROMPT 12: Kullanıcı tarafı destek talebi oluşturma (/api/v1/support/*)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth
import models
from database import get_db

router = APIRouter(prefix="/api/v1/support", tags=["support"])


class TicketCreateRequest(BaseModel):
    subject: str
    message: str
    category: str = "other"  # billing | bug | feature_request | other


@router.post("/tickets")
def create_ticket(body: TicketCreateRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    ticket = models.SupportTicket(user_id=current_user.id, subject=body.subject, category=body.category)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    db.add(models.SupportTicketMessage(ticket_id=ticket.id, author_user_id=current_user.id, is_admin_reply=False, message=body.message))
    db.commit()
    return {"id": ticket.id, "status": ticket.status}


@router.get("/tickets")
def list_my_tickets(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    tickets = db.query(models.SupportTicket).filter(models.SupportTicket.user_id == current_user.id).order_by(models.SupportTicket.created_at.desc()).all()
    return [{"id": t.id, "subject": t.subject, "status": t.status, "category": t.category, "created_at": t.created_at} for t in tickets]


@router.get("/tickets/{ticket_id}")
def get_ticket_thread(ticket_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id, models.SupportTicket.user_id == current_user.id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Destek talebi bulunamadı.")
    messages = db.query(models.SupportTicketMessage).filter(models.SupportTicketMessage.ticket_id == ticket_id).order_by(models.SupportTicketMessage.created_at).all()
    return {
        "id": ticket.id, "subject": ticket.subject, "status": ticket.status,
        "messages": [{"is_admin_reply": m.is_admin_reply, "message": m.message, "created_at": m.created_at} for m in messages],
    }
