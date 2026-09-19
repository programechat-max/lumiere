"""body_composition tablosu: InBody benzeri genel + segmentel olcumler

Revision ID: j9e1f3a5b7c8
Revises: i8d0e2f4a6b7
Create Date: 2026-09-19

Kisisel Bilgiler sayfasinin ve onboarding "Vucut Analizi" adiminin veri kaynagi.
Tum olcum kolonlari NULL kabul eder: kullanici cihaz ciktisindan yalnizca
okuyabildigi degerleri girer. Segment kolonlari cihaz konvansiyonuna uyar
(sag/sol bacak, sag/sol kol, govde). 'review' JSON alani Jarvis'in fark
degerlendirmesini tasir; arayuzdeki kirmizi/yesil renk yalnizca bunun
sentiment alanindan gelir.

Tablo zaten varsa (orn. SQLite'da create_all ile olusmus) idempotent davranir.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j9e1f3a5b7c8"
down_revision: Union[str, Sequence[str], None] = "i8d0e2f4a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "body_composition"

SEGMENTS = ("right_leg", "left_leg", "right_arm", "left_arm", "trunk")


def _columns() -> list:
    cols = [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="manual"),
        # Genel olcumler
        sa.Column("body_fat_percent", sa.Float(), nullable=True),
        sa.Column("total_fat_kg", sa.Float(), nullable=True),
        sa.Column("lean_mass_kg", sa.Float(), nullable=True),
        sa.Column("muscle_kg", sa.Float(), nullable=True),
        sa.Column("bone_mass_kg", sa.Float(), nullable=True),
        sa.Column("body_water_kg", sa.Float(), nullable=True),
    ]
    for suffix in ("fat_percent", "muscle_kg", "fat_kg"):
        for segment in SEGMENTS:
            cols.append(sa.Column(f"{segment}_{suffix}", sa.Float(), nullable=True))
    cols += [
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("review", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    ]
    return cols


def upgrade() -> None:
    conn = op.get_bind()
    if TABLE_NAME in set(sa.inspect(conn).get_table_names()):
        return  # idempotent: tablo zaten varsa dokunma
    op.create_table(TABLE_NAME, *_columns())
    op.create_index(op.f(f"ix_{TABLE_NAME}_id"), TABLE_NAME, ["id"])
    op.create_index(op.f(f"ix_{TABLE_NAME}_user_id"), TABLE_NAME, ["user_id"])
    op.create_index(op.f(f"ix_{TABLE_NAME}_date"), TABLE_NAME, ["date"])


def downgrade() -> None:
    if TABLE_NAME in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table(TABLE_NAME)