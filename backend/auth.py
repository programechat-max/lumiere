"""
Kimlik doğrulama & yetkilendirme modülü (PROMPT 2).

Kapsam:
  - Argon2 şifre hashleme (eski bcrypt hash'leri ile geriye dönük uyumlu -
    kullanıcı giriş yaptığında otomatik olarak Argon2'ye yükseltilir)
  - Kısa ömürlü JWT access token (varsayılan 15dk) + veritabanında saklanan,
    hash'lenmiş refresh token (varsayılan 7 gün, HttpOnly cookie'de taşınır)
  - Başarısız giriş kilitlemesi (5 deneme -> 15dk kilit)
  - Rol tabanlı yetkilendirme (RBAC) dependency'leri
  - Audit log yardımcı fonksiyonu

Ortam değişkenleri: bkz. backend/config.py ve .env.example
"""
import hashlib
import os
import secrets
import datetime
from typing import Optional, List

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
from config import settings
from database import get_db

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# Argon2 birincil şema; bcrypt eski hash'leri doğrulamak için "deprecated" olarak tutulur.
# Bu sayede mevcut kullanıcı hesapları bozulmadan yeni algoritmaya kademeli geçiş yapılır.
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"


# ==========================================
# ŞİFRE HASHLEME
# ==========================================
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    """Eski bcrypt hash'lerini tespit eder; login sonrası Argon2'ye yükseltmek için kullanılır."""
    return pwd_context.needs_update(hashed_password)


def validate_password_strength(password: str) -> Optional[str]:
    """Şifre karmaşıklık kurallarını kontrol eder. Hata yoksa None döner."""
    if len(password) < 12:
        return "Şifre en az 12 karakter olmalı."
    if not any(c.isupper() for c in password):
        return "Şifre en az bir büyük harf içermeli."
    if not any(c.islower() for c in password):
        return "Şifre en az bir küçük harf içermeli."
    if not any(c.isdigit() for c in password):
        return "Şifre en az bir rakam içermeli."
    if not any(not c.isalnum() for c in password):
        return "Şifre en az bir özel karakter içermeli."
    return None


# ==========================================
# JWT ACCESS TOKEN
# ==========================================
def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ==========================================
# REFRESH TOKEN (DB'de hash'lenmiş olarak saklanır - UserSession)
# ==========================================
def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_refresh_token(
    db: Session,
    user_id: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    device_name: Optional[str] = None,
) -> str:
    """Yeni bir refresh token üretir, hash'ini UserSession tablosuna kaydeder.
    Eşzamanlı oturum limitini aşan en eski oturumları otomatik iptal eder."""
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    session = models.UserSession(
        user_id=user_id,
        refresh_token_hash=_hash_token(raw_token),
        device_name=device_name,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()

    active_sessions = (
        db.query(models.UserSession)
        .filter(models.UserSession.user_id == user_id, models.UserSession.revoked_at.is_(None))
        .order_by(models.UserSession.created_at.desc())
        .all()
    )
    for stale in active_sessions[settings.MAX_CONCURRENT_SESSIONS:]:
        stale.revoked_at = datetime.datetime.utcnow()
    if len(active_sessions) > settings.MAX_CONCURRENT_SESSIONS:
        db.commit()

    return raw_token


def rotate_refresh_token(db: Session, raw_token: str) -> Optional[models.UserSession]:
    """Verilen refresh token geçerliyse ilgili oturumu döner (rotasyon çağıran tarafta yapılır)."""
    token_hash = _hash_token(raw_token)
    session = (
        db.query(models.UserSession)
        .filter(models.UserSession.refresh_token_hash == token_hash)
        .first()
    )
    if not session:
        return None
    if session.revoked_at is not None:
        return None
    if session.expires_at < datetime.datetime.utcnow():
        return None
    inactivity_cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=settings.SESSION_INACTIVITY_DAYS)
    if session.last_active_at and session.last_active_at < inactivity_cutoff:
        session.revoked_at = datetime.datetime.utcnow()
        db.commit()
        return None
    session.last_active_at = datetime.datetime.utcnow()
    db.commit()
    return session


def revoke_session(db: Session, session_id: int, user_id: int) -> bool:
    session = (
        db.query(models.UserSession)
        .filter(models.UserSession.id == session_id, models.UserSession.user_id == user_id)
        .first()
    )
    if not session:
        return False
    session.revoked_at = datetime.datetime.utcnow()
    db.commit()
    return True


def revoke_session_by_raw_token(db: Session, raw_token: str) -> None:
    token_hash = _hash_token(raw_token)
    session = db.query(models.UserSession).filter(models.UserSession.refresh_token_hash == token_hash).first()
    if session and session.revoked_at is None:
        session.revoked_at = datetime.datetime.utcnow()
        db.commit()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


# ==========================================
# KULLANICI SORGULARI
# ==========================================
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email.lower().strip()).first()


def is_account_locked(user: models.User) -> bool:
    return bool(user.locked_until and user.locked_until > datetime.datetime.utcnow())


def register_failed_login(db: Session, user: models.User) -> None:
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
    db.commit()


def register_successful_login(db: Session, user: models.User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if is_account_locked(user):
        return None
    if not verify_password(password, user.hashed_password):
        register_failed_login(db, user)
        return None
    if user.is_suspended:
        return None
    # Kademeli Argon2 yükseltmesi: eski bcrypt hash'i doğrulandıysa hemen yeniden hashle.
    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(password)
    register_successful_login(db, user)
    return user


# ==========================================
# FASTAPI DEPENDENCY'LERİ
# ==========================================
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulanamadı. Lütfen tekrar giriş yapın.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None or not user.is_active or user.is_suspended:
        raise credentials_exception
    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    """Giriş zorunlu olmayan uçlar için: token varsa kullanıcıyı döner, yoksa None."""
    if token is None:
        return None
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    return db.query(models.User).filter(models.User.id == int(user_id)).first()


def require_roles(*roles: str):
    """RBAC dependency factory: `Depends(require_roles("ADMIN", "SUPER_ADMIN"))`."""
    allowed = {r.upper() for r in roles}

    def dependency(current_user: models.User = Depends(get_current_user)) -> models.User:
        if (current_user.role or "USER").upper() not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem için yetkiniz yok.")
        return current_user

    return dependency


require_admin = require_roles("ADMIN", "SUPER_ADMIN")
require_support = require_roles("ADMIN", "SUPER_ADMIN", "SUPPORT")
require_finance = require_roles("ADMIN", "SUPER_ADMIN", "FINANCE")


# ==========================================
# AUDIT LOG
# ==========================================
def get_client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def log_audit(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    actor_user_id: Optional[int] = None,
    result: str = "success",
    request: Optional[Request] = None,
    resource: Optional[str] = None,
    meta: Optional[dict] = None,
) -> None:
    try:
        entry = models.AuditLog(
            user_id=user_id,
            actor_user_id=actor_user_id if actor_user_id is not None else user_id,
            action=action,
            resource=resource,
            result=result,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent") if request else None,
            meta=meta or {},
        )
        db.add(entry)
        db.commit()
    except Exception:
        # Audit log yazımı ana iş akışını asla bozmamalı.
        db.rollback()
