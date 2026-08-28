"""
PROMPT 2 & PROMPT 8: Kurumsal kimlik doğrulama uçları (/api/v1/auth/*).

Legacy /api/auth/* uçları (main.py) geriye dönük uyumluluk için AYNEN korunur
(access_token'ı gövdede döner, frontend hâlâ localStorage kullanabilir). Bu yeni
v1 uçları ise HttpOnly refresh-token cookie + CSRF double-submit deseniyle
XSS/CSRF riskini azaltan önerilen akıştır (bkz. src/services/authService.js).
"""
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

import auth
import billing_service
import crud
import models
import schemas
from config import settings
from database import get_db
from rate_limit import check_rate_limit

router = APIRouter(prefix="/api/v1/auth", tags=["auth-v1"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)


class ConsentBody(BaseModel):
    data_processing: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    analytics: Optional[bool] = None


def _set_auth_cookies(response: Response, refresh_token: str, csrf_token: str) -> None:
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    response.set_cookie(
        auth.REFRESH_COOKIE_NAME, refresh_token, httponly=True, secure=settings.COOKIE_SECURE,
        samesite="lax", max_age=max_age, path="/api/v1/auth", domain=settings.COOKIE_DOMAIN,
    )
    response.set_cookie(
        auth.CSRF_COOKIE_NAME, csrf_token, httponly=False, secure=settings.COOKIE_SECURE,
        samesite="lax", max_age=max_age, path="/", domain=settings.COOKIE_DOMAIN,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(auth.REFRESH_COOKIE_NAME, path="/api/v1/auth", domain=settings.COOKIE_DOMAIN)
    response.delete_cookie(auth.CSRF_COOKIE_NAME, path="/", domain=settings.COOKIE_DOMAIN)


def _issue_tokens(db: Session, response: Response, user: models.User, request: Request) -> str:
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    refresh_token = auth.create_refresh_token(
        db, user.id,
        ip_address=auth.get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    csrf_token = auth.generate_csrf_token()
    _set_auth_cookies(response, refresh_token, csrf_token)
    return access_token


@router.post("/register", response_model=schemas.TokenResponse)
def register_v1(user_data: schemas.UserCreate, request: Request, response: Response, db: Session = Depends(get_db)):
    if auth.get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=409, detail="Bu e-posta adresi zaten kullanımda.")
    weakness = auth.validate_password_strength(user_data.password)
    if weakness:
        raise HTTPException(status_code=422, detail=weakness)

    # Kayıt sırasında seçilen üyelik planı (Free/Pro/Elite/Elite+) doğrulanır;
    # geçersizse güvenli şekilde FREE'e düşer.
    plan = (user_data.preferred_plan or "FREE").upper().strip()
    if plan not in ("FREE", "PRO", "ELITE", "ELITE_PLUS"):
        plan = "FREE"

    new_user = models.User(
        full_name=user_data.full_name,
        email=user_data.email.lower().strip(),
        hashed_password=auth.hash_password(user_data.password),
        role="ADMIN" if user_data.email.lower().strip() in settings.admin_bootstrap_emails_list else "USER",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Profil + üyelik kaydını hemen oluştur; seçilen planı yaz.
    profile = crud.get_or_create_profile(db, new_user.id)
    profile.preferred_plan = plan
    db.commit()
    sub = billing_service.get_or_create_subscription(db, new_user.id)
    sub.plan_type = plan
    db.commit()

    access_token = _issue_tokens(db, response, new_user, request)
    auth.log_audit(db, "register", user_id=new_user.id, request=request)
    return schemas.TokenResponse(access_token=access_token, user=new_user)


@router.post("/login", response_model=schemas.TokenResponse)
def login_v1(credentials: schemas.UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = auth.get_client_ip(request) or "unknown"
    limit_result = check_rate_limit(f"login:{client_ip}", settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60)
    if not limit_result.allowed:
        raise HTTPException(status_code=429, detail="Çok fazla giriş denemesi. Lütfen bir dakika sonra tekrar deneyin.",
                             headers=limit_result.headers)

    user = auth.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        auth.log_audit(db, "login_failed", request=request, meta={"email": credentials.email.lower().strip()}, result="failure")
        # Kullanıcı numaralandırmasını (enumeration) önlemek için jenerik hata mesajı.
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı.")

    access_token = _issue_tokens(db, response, user, request)
    auth.log_audit(db, "login_success", user_id=user.id, request=request)
    return schemas.TokenResponse(access_token=access_token, user=user)


@router.post("/refresh")
def refresh_token_v1(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_refresh = request.cookies.get(auth.REFRESH_COOKIE_NAME)
    csrf_cookie = request.cookies.get(auth.CSRF_COOKIE_NAME)
    csrf_header = request.headers.get("x-csrf-token")

    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Oturum bulunamadı, lütfen tekrar giriş yapın.")
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(status_code=403, detail="CSRF doğrulaması başarısız.")

    session = auth.rotate_refresh_token(db, raw_refresh)
    if not session:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Oturum süresi doldu, lütfen tekrar giriş yapın.")

    user = db.query(models.User).filter(models.User.id == session.user_id).first()
    if not user or not user.is_active or user.is_suspended:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı veya devre dışı.")

    # Refresh token rotasyonu: eskisini iptal et, yenisini ver (token replay saldırılarını sınırlar).
    session.revoked_at = datetime.datetime.utcnow()
    db.commit()
    access_token = _issue_tokens(db, response, user, request)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout_v1(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_refresh = request.cookies.get(auth.REFRESH_COOKIE_NAME)
    if raw_refresh:
        auth.revoke_session_by_raw_token(db, raw_refresh)
    _clear_auth_cookies(response)
    return {"status": "logged_out"}


@router.get("/sessions")
def list_sessions(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(models.UserSession)
        .filter(models.UserSession.user_id == current_user.id, models.UserSession.revoked_at.is_(None))
        .order_by(models.UserSession.created_at.desc())
        .all()
    )
    return [
        {
            "id": s.id, "device_name": s.device_name, "ip_address": s.ip_address,
            "user_agent": s.user_agent, "created_at": s.created_at, "last_active_at": s.last_active_at,
            "expires_at": s.expires_at,
        }
        for s in sessions
    ]


@router.post("/sessions/{session_id}/revoke")
def revoke_session_endpoint(session_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if not auth.revoke_session(db, session_id, current_user.id):
        raise HTTPException(status_code=404, detail="Oturum bulunamadı.")
    return {"status": "revoked"}


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, request: Request, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if not auth.verify_password(body.current_password, current_user.hashed_password):
        auth.log_audit(db, "password_change_failed", user_id=current_user.id, request=request, result="failure")
        raise HTTPException(status_code=401, detail="Mevcut şifre hatalı.")
    weakness = auth.validate_password_strength(body.new_password)
    if weakness:
        raise HTTPException(status_code=422, detail=weakness)

    current_user.hashed_password = auth.hash_password(body.new_password)
    # Şifre değişince tüm mevcut oturumlar (bu isteğin kendisi hariç değil - basitlik için hepsi) iptal edilir.
    db.query(models.UserSession).filter(
        models.UserSession.user_id == current_user.id, models.UserSession.revoked_at.is_(None)
    ).update({"revoked_at": datetime.datetime.utcnow()})
    db.commit()
    auth.log_audit(db, "password_change_success", user_id=current_user.id, request=request)
    return {"status": "password_updated"}


@router.get("/login-history")
def login_history(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    logs = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.user_id == current_user.id, models.AuditLog.action.in_(["login_success", "login_failed", "logout"]))
        .order_by(models.AuditLog.created_at.desc())
        .limit(50)
        .all()
    )
    return [{"action": l.action, "ip_address": l.ip_address, "result": l.result, "created_at": l.created_at} for l in logs]
