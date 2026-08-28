"""
Sayfalama yardımcıları (PROMPT 6).

- `paginate_query`: limit/offset tabanlı klasik sayfalama (toplam sayım ile).
- `cursor_paginate`: zaman serisi (created_at bazlı) veriler için imleç (cursor)
  tabanlı sayfalama - büyük tablolarda pahalı COUNT(*) sorgusundan kaçınır.
"""
import base64
import datetime
from typing import Optional

from fastapi import Query
from sqlalchemy.orm import Query as SAQuery

DEFAULT_LIMIT = 50
MAX_LIMIT = 1000


def pagination_params(limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT), offset: int = Query(0, ge=0)):
    return {"limit": limit, "offset": offset}


def paginate_query(query: SAQuery, limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict:
    total = query.order_by(None).count()
    items = query.offset(offset).limit(limit).all()
    return {"data": items, "total": total, "limit": limit, "offset": offset}


def encode_cursor(value: datetime.datetime) -> str:
    return base64.urlsafe_b64encode(value.isoformat().encode()).decode()


def decode_cursor(cursor: str) -> Optional[datetime.datetime]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        return datetime.datetime.fromisoformat(raw)
    except Exception:
        return None


def cursor_paginate(query: SAQuery, cursor_column, cursor: Optional[str] = None, limit: int = DEFAULT_LIMIT) -> dict:
    """`cursor_column` üzerinde (örn. Model.created_at) azalan sıralı imleç sayfalaması."""
    if cursor:
        after = decode_cursor(cursor)
        if after:
            query = query.filter(cursor_column < after)
    items = query.order_by(cursor_column.desc()).limit(limit + 1).all()
    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = encode_cursor(getattr(items[-1], cursor_column.key)) if has_more and items else None
    return {"data": items, "limit": limit, "next_cursor": next_cursor}
