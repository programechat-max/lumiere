"""PROMPT 4: Dosya depolama uçları (/api/v1/files/*). S3 yapılandırılmamışsa
presigned-url uçları 501 döner; mevcut yerel onboarding akışı bundan etkilenmez."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth
import models
import storage
from database import get_db
from pagination import paginate_query

router = APIRouter(prefix="/api/v1/files", tags=["files"])


class PresignedUrlRequest(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int
    category: str = "general"


class ConfirmUploadRequest(BaseModel):
    file_id: int


@router.post("/presigned-url")
def get_presigned_url(body: PresignedUrlRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    error = storage.validate_upload(body.mime_type, body.size_bytes)
    if error:
        raise HTTPException(status_code=400, detail=error)

    object_key = storage.build_object_key(current_user.id, body.category, body.filename)
    presigned = storage.generate_presigned_upload_url(object_key, body.mime_type)
    if not presigned:
        raise HTTPException(status_code=501, detail="Bulut depolama (S3) henüz yapılandırılmadı. AWS_ACCESS_KEY_ID/S3_BUCKET_NAME ortam değişkenlerini tanımlayın.")

    file_asset = models.FileAsset(
        user_id=current_user.id, s3_key=object_key, original_filename=body.filename,
        size_bytes=body.size_bytes, mime_type=body.mime_type, category=body.category,
        processing_status="pending",
    )
    db.add(file_asset)
    db.commit()
    db.refresh(file_asset)
    return {**presigned, "file_id": file_asset.id}


@router.post("/confirm")
def confirm_upload(body: ConfirmUploadRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    file_asset = (
        db.query(models.FileAsset)
        .filter(models.FileAsset.id == body.file_id, models.FileAsset.user_id == current_user.id)
        .first()
    )
    if not file_asset:
        raise HTTPException(status_code=404, detail="Dosya kaydı bulunamadı.")
    file_asset.processing_status = "uploaded"
    file_asset.scan_status = "skipped"  # ClamAV/VirusTotal entegrasyonu yapılandırılana kadar
    db.commit()
    return {"status": "confirmed", "file_id": file_asset.id}


@router.get("/{file_id}")
def get_file(file_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    file_asset = (
        db.query(models.FileAsset)
        .filter(models.FileAsset.id == file_id, models.FileAsset.user_id == current_user.id, models.FileAsset.is_deleted == False)  # noqa: E712
        .first()
    )
    if not file_asset:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    download_url = storage.generate_presigned_download_url(file_asset.s3_key)
    return {
        "id": file_asset.id, "filename": file_asset.original_filename, "mime_type": file_asset.mime_type,
        "processing_status": file_asset.processing_status, "download_url": download_url,
        "created_at": file_asset.created_at,
    }


@router.delete("/{file_id}")
def delete_file(file_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    file_asset = (
        db.query(models.FileAsset)
        .filter(models.FileAsset.id == file_id, models.FileAsset.user_id == current_user.id)
        .first()
    )
    if not file_asset:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    storage.delete_object(file_asset.s3_key)
    file_asset.is_deleted = True
    db.commit()
    return {"status": "deleted"}


@router.get("")
def list_files(limit: int = Query(50, ge=1, le=1000), offset: int = Query(0, ge=0), current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    query = db.query(models.FileAsset).filter(models.FileAsset.user_id == current_user.id, models.FileAsset.is_deleted == False)  # noqa: E712
    query = query.order_by(models.FileAsset.created_at.desc())
    return paginate_query(query, limit=limit, offset=offset)
