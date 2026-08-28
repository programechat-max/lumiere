"""
PROMPT 10: Yeni platform yükseltmesi özellikleri için test paketi.
Harici bulut hesapları (Stripe/AWS/APNs/Sentry) YAPILANDIRILMADIĞI için bu testler
o entegrasyonların "yapılandırılmamış -> güvenli no-op/503" davranışını doğrular;
gerçek Stripe/APNs hesabıyla webhook/push testleri ayrıca mock'lanır.
"""
import datetime
import time

import auth
import billing_service
import models
import notification_service
import privacy
from pagination import paginate_query
from rate_limit import check_rate_limit


# ==========================================
# AUTH v1: refresh cookie + CSRF + oturum yönetimi
# ==========================================
def test_v1_register_sets_refresh_and_csrf_cookies(client):
    res = client.post("/api/v1/auth/register", json={
        "full_name": "Yeni Kullanıcı", "email": "v1user@test.com", "password": "GucluSifre!2024",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert auth.REFRESH_COOKIE_NAME in res.cookies
    assert auth.CSRF_COOKIE_NAME in res.cookies


def test_v1_refresh_requires_csrf_header(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "CSRF Test", "email": "csrftest@test.com", "password": "GucluSifre!2024",
    })
    # CSRF header eksik -> 403 bekleniyor.
    res = client.post("/api/v1/auth/refresh")
    assert res.status_code == 403


def test_v1_refresh_rotates_token(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Rotasyon Test", "email": "rotate@test.com", "password": "GucluSifre!2024",
    })
    csrf_token = client.cookies.get(auth.CSRF_COOKIE_NAME)
    res = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_v1_login_wrong_password_generic_message(client, test_user):
    res = client.post("/api/v1/auth/login", json={"email": test_user.email, "password": "yanlis-sifre"})
    assert res.status_code == 401
    assert res.json()["detail"] == "E-posta veya şifre hatalı."


def test_account_lockout_after_max_failed_attempts(db_session, test_user):
    for _ in range(5):
        auth.authenticate_user(db_session, test_user.email, "yanlis-sifre")
    db_session.refresh(test_user)
    assert auth.is_account_locked(test_user)
    # Doğru şifreyle bile giriş kilitliyken engellenmeli.
    assert auth.authenticate_user(db_session, test_user.email, "testpassword123") is None


def test_password_strength_validation():
    assert auth.validate_password_strength("short") is not None
    assert auth.validate_password_strength("NoDigitsOrSymbolsHere") is not None
    assert auth.validate_password_strength("Gucl1Sifre!2024") is None


def test_rbac_blocks_non_admin(client, auth_headers):
    res = client.get("/api/v1/admin/users", headers=auth_headers)
    assert res.status_code == 403


def test_rbac_allows_admin(db_session, client, test_user, auth_headers):
    test_user.role = "ADMIN"
    db_session.commit()
    res = client.get("/api/v1/admin/users", headers=auth_headers)
    assert res.status_code == 200
    assert "data" in res.json()


# ==========================================
# RATE LIMITING & PAGINATION
# ==========================================
def test_rate_limit_blocks_after_threshold():
    key = f"unit-test-{time.time()}"
    results = [check_rate_limit(key, limit=3, window_seconds=60) for _ in range(4)]
    assert results[0].allowed and results[1].allowed and results[2].allowed
    assert not results[3].allowed


def test_pagination_returns_total_and_slices(db_session, test_user):
    for i in range(5):
        db_session.add(models.BodyMetric(user_id=test_user.id, date=datetime.date.today(), weight=70 + i))
    db_session.commit()
    query = db_session.query(models.BodyMetric).filter(models.BodyMetric.user_id == test_user.id)
    page = paginate_query(query, limit=2, offset=0)
    assert page["total"] == 5
    assert len(page["data"]) == 2


# ==========================================
# BİLLİNG (Stripe yapılandırılmamış senaryosu)
# ==========================================
def test_subscription_defaults_to_free(db_session, test_user):
    sub = billing_service.get_or_create_subscription(db_session, test_user.id)
    assert sub.plan_type == "FREE"
    assert billing_service.has_feature_access(sub, "ai_chat") is False


def test_trial_start_grants_feature_access(db_session, test_user):
    sub = billing_service.start_trial(db_session, test_user.id, "PREMIUM_MONTHLY")
    assert sub.status == "trialing"
    assert billing_service.has_feature_access(sub, "ai_chat") is True


def test_checkout_without_stripe_config_returns_503(client, auth_headers):
    res = client.post("/api/v1/billing/checkout", json={"plan_type": "PREMIUM_MONTHLY"}, headers=auth_headers)
    assert res.status_code == 503


# ==========================================
# NOTIFICATIONS (APNs yapılandırılmamış senaryosu)
# ==========================================
def test_device_token_lifecycle(client, auth_headers):
    res = client.post("/api/v1/notifications/devices", json={"token": "abc123devicetoken", "platform": "ios"}, headers=auth_headers)
    assert res.status_code == 200
    res2 = client.delete("/api/v1/notifications/devices/abc123devicetoken", headers=auth_headers)
    assert res2.status_code == 200


def test_quiet_hours_detection(db_session, test_user):
    settings_row = notification_service.get_or_create_settings(db_session, test_user.id)
    settings_row.quiet_hours_start = "22:00"
    settings_row.quiet_hours_end = "08:00"
    db_session.commit()
    assert notification_service.is_within_quiet_hours(settings_row, now=datetime.time(23, 0)) is True
    assert notification_service.is_within_quiet_hours(settings_row, now=datetime.time(12, 0)) is False


def test_dispatch_skips_when_no_devices(db_session, test_user):
    result = notification_service.dispatch_to_user(db_session, test_user.id, "daily_checkin", "Merhaba", "Test")
    assert result["status"] == "skipped"
    assert result["reason"] == "no_active_devices"


# ==========================================
# GDPR / PRIVACY
# ==========================================
def test_data_export_contains_expected_sections(db_session, test_user):
    export = privacy.build_user_data_export(test_user.id, db=db_session)
    assert "user" in export
    assert "workout_logs" in export
    assert "hashed_password" not in export["user"]


def test_account_deletion_request_and_cancel(db_session, test_user):
    request = privacy.request_account_deletion(db_session, test_user.id)
    assert request.status == "pending"
    assert privacy.cancel_account_deletion(db_session, test_user.id, request.cancel_token) is True


def test_consent_recording(db_session, test_user):
    privacy.record_consent(db_session, test_user.id, "marketing_emails", True, "127.0.0.1", "pytest")
    consents = privacy.get_latest_consents(db_session, test_user.id)
    assert consents["marketing_emails"]["granted"] is True


# ==========================================
# HEALTH / MONITORING
# ==========================================
def test_chat_endpoint_with_plan_rate_limit_dependency(client, auth_headers, monkeypatch):
    """PROMPT 6: /api/chat artık enforce_plan_rate_limit dependency'si içeriyor -
    bu testin amacı o dependency eklendiğinde endpoint'in hala çalıştığını doğrulamak
    (regresyon testi)."""
    import ai_core

    monkeypatch.setattr(ai_core, "process_message", lambda *a, **k: {"intent": "chat", "jarvis_reply": "test"})
    res = client.post("/api/chat", json={"message": "selam"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["jarvis_reply"] == "test"


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_ready_endpoint_reports_database(client):
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["checks"]["database"]["status"] == "ok"
