"""Production sema suruklenmesi onarimi: exercise_library_items eksik kolonlari ekle.

Revision ID: k0a1b2c3d4e5
Revises: j9e1f3a5b7c8
Create Date: 2026-09-19

KOK NEDEN: Canli (Render) Postgres'te Alembic migration'lari startup'ta hic
calistirilmadigi icin (Dockerfile yalnizca `uvicorn` aciyordu) tablo eski
semada kaldi. Model ise bu kolonlari bekliyor -> selector sorgusu
'column does not exist' ile patladi -> InFailedSqlTransaction.

Bu migration tamamen IDEMPOTENT: her kolon icin once varligini kontrol eder,
varsa atlar. Boylece hem eksik semayi toparlar hem de tekrar calistirilinca
zararsizdir. Oncelikle onceki revizyonlar (c9d5..i8d0) idempotent oldugu icin
bu, ek bir guvenlik agi / hizli onarim saglar.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "j9e1f3a5b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (kolon_adi, tip) — modelde beklenen Faz 6/7 + kanit/kurasyon kolonlari.
EXERCISE_LIBRARY_COLUMNS = [
    # Faz 6
    ("difficulty", sa.String()),
    ("force_type", sa.String()),
    ("mechanic", sa.String()),
    ("goals", sa.String()),
    ("tags", sa.String()),
    ("met", sa.Float()),
    ("body_part", sa.String()),
    ("description", sa.Text()),
    ("image_start", sa.String()),
    ("image_peak", sa.String()),
    ("image_main", sa.String()),
    ("is_bodyweight", sa.Boolean()),
    ("source", sa.String()),
    # Faz 7
    ("muscle_head", sa.String()),
    ("stimulus_rating", sa.Float()),
    ("rom_profile", sa.String()),
    # Kanit kalitesi + kurasyon
    ("evidence_level", sa.String()),
    ("evidence_source", sa.String()),
    ("evidence_scope", sa.String()),
    ("reviewed_by", sa.String()),
    ("reviewed_at", sa.DateTime()),
    ("review_note", sa.Text()),
]


def _existing_columns(conn, table: str) -> set:
    return {c["name"] for c in sa.inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if "exercise_library_items" not in set(sa.inspect(conn).get_table_names()):
        return
    existing = _existing_columns(conn, "exercise_library_items")
    added = []
    for name, col_type in EXERCISE_LIBRARY_COLUMNS:
        if name in existing:
            continue
        op.add_column("exercise_library_items", sa.Column(name, col_type, nullable=True))
        added.append(name)
    if added:
        print(f"[k0a1b2c3d4e5] exercise_library_items'a eklenen kolonlar: {added}")


def downgrade() -> None:
    # Guvenlik: bu onarim migration'i geri alinmaz (eksik kolonlar silinmez).
    pass
