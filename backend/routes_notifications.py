"""PROMPT 9: iOS APNs cihaz token yönetimi ve bildirim tercihleri (/api/v1/notifications/*)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import auth
import models
import notification_service
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class DeviceRegisterRequest(BaseModel):
    token: str
    platform: str = "ios"
    device_name: Optional[str] = None


class NotificationSettingsUpdate(BaseModel):
    daily_checkin_enabled: Optional[bool] = None
    workout_reminders_enabled: Optional[bool] = None
    weekly_report_enabled: Optional[bool] = None
    inactivity_alerts_enabled: Optional[bool] = None
    billing_alerts_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: Optional[str] = None


@router.post("/devices")
def register_device(body: DeviceRegisterRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    device = notification_service.register_device_token(db, current_user.id, body.token, body.platform, body.device_name)
    return {"id": device.id, "status": "registered"}


@router.delete("/devices/{token}")
def unregister_device(token: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if not notification_service.unregister_device_token(db, current_user.id, token):
        raise HTTPException(status_code=404, detail="Cihaz token'ı bulunamadı.")
    return {"status": "unregistered"}


@router.get("/settings")
def get_settings_endpoint(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    row = notification_service.get_or_create_settings(db, current_user.id)
    return {
        "daily_checkin_enabled": row.daily_checkin_enabled,
        "workout_reminders_enabled": row.workout_reminders_enabled,
        "weekly_report_enabled": row.weekly_report_enabled,
        "inactivity_alerts_enabled": row.inactivity_alerts_enabled,
        "billing_alerts_enabled": row.billing_alerts_enabled,
        "quiet_hours_start": row.quiet_hours_start,
        "quiet_hours_end": row.quiet_hours_end,
        "timezone": row.timezone,
    }


@router.put("/settings")
def update_settings_endpoint(body: NotificationSettingsUpdate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    row = notification_service.update_settings(db, current_user.id, body.model_dump(exclude_unset=True))
    return {"status": "updated", "settings": {
        "daily_checkin_enabled": row.daily_checkin_enabled,
        "workout_reminders_enabled": row.workout_reminders_enabled,
        "weekly_report_enabled": row.weekly_report_enabled,
        "inactivity_alerts_enabled": row.inactivity_alerts_enabled,
        "billing_alerts_enabled": row.billing_alerts_enabled,
        "quiet_hours_start": row.quiet_hours_start,
        "quiet_hours_end": row.quiet_hours_end,
        "timezone": row.timezone,
    }}
