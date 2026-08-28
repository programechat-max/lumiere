"""PROMPT 11: GDPR/gizlilik uçları (/api/v1/privacy/*)."""
import gzip
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth
import models
import privacy
from database import get_db
from rate_limit import check_rate_limit

router = APIRouter(prefix="/api/v1/privacy", tags=["privacy"])


class ConsentRequest(BaseModel):
    consent_type: str  # data_processing | marketing_emails | analytics
    granted: bool


class CancelDeletionRequest(BaseModel):
    cancel_token: str


@router.get("/export")
def export_my_data(request: Request, current_user: models.User = Depends(auth.get_current_user)):
    """Kullanıcının tüm verisini gzip'lenmiş JSON olarak indirir.
    Kötüye kullanımı önlemek için ayda 1 talep ile sınırlıdır."""
    limit_result = check_rate_limit(f"data_export:{current_user.id}", limit=1, window_seconds=30 * 24 * 3600)
    if not limit_result.allowed:
        raise HTTPException(status_code=429, detail="Veri dışa aktarma talebi ayda bir kez yapılabilir.")

    data = privacy.build_user_data_export(current_user.id)
    payload = gzip.compress(json.dumps(data, default=str, ensure_ascii=False).encode("utf-8"))
    return Response(
        content=payload, media_type="application/gzip",
        headers={"Content-Disposition": f"attachment; filename=lumiere-data-export-{current_user.id}.json.gz"},
    )


@router.post("/delete-account")
def delete_account(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    request = privacy.request_account_deletion(db, current_user.id)
    return {
        "status": "deletion_scheduled",
        "scheduled_for": request.scheduled_for,
        "cancel_token": request.cancel_token,
        "message": "Hesabınız 30 gün sonra kalıcı olarak silinecek. Bu süre içinde iptal edebilirsiniz.",
    }


@router.post("/cancel-deletion")
def cancel_deletion(body: CancelDeletionRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if not privacy.cancel_account_deletion(db, current_user.id, body.cancel_token):
        raise HTTPException(status_code=404, detail="Bekleyen bir silme talebi bulunamadı veya token geçersiz.")
    return {"status": "deletion_canceled"}


@router.post("/consent")
def set_consent(body: ConsentRequest, request: Request, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    consent = privacy.record_consent(
        db, current_user.id, body.consent_type, body.granted,
        ip_address=auth.get_client_ip(request), user_agent=request.headers.get("user-agent"),
    )
    return {"status": "recorded", "consent_type": consent.consent_type, "granted": consent.granted}


@router.get("/consent")
def get_consent(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return privacy.get_latest_consents(db, current_user.id)
