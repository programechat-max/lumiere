"""Faz 7 - kanita dayali hipertrofi + makro/mikro dogrulama katmani.

- food_items: mikro besin kolonlari (sodium/potassium/calcium/iron/magnesium/zinc/D/B12/C) + micro_reference
- exercise_library_items: muscle_head, stimulus_rating, rom_profile
- nutrition_logs: verification_source, verified, confidence, micros, items_breakdown
- yeni tablo: evidence_topics (Jarvis "Neden X yerine Y?" kanit bankasi)

Revision ID: d7e1f5a3c2b4
Revises: c9d5e8f3a2b1
Create Date: 2026-09-11

SQLite create_all ile uyumlu: kolon zaten varsa atlar (idempotent).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd7e1f5a3c2b4'
down_revision: Union[str, Sequence[str], None] = 'c9d5e8f3a2b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FOOD_MICRO_COLUMNS = [
    ("sodium_mg", sa.Float()),
    ("potassium_mg", sa.Float()),
    ("calcium_mg", sa.Float()),
    ("iron_mg", sa.Float()),
    ("magnesium_mg", sa.Float()),
    ("zinc_mg", sa.Float()),
    ("vitamin_d_ug", sa.Float()),
    ("vitamin_b12_ug", sa.Float()),
    ("vitamin_c_mg", sa.Float()),
    ("micro_reference", sa.JSON()),
]

EXERCISE_COLUMNS = [
    ("muscle_head", sa.String()),
    ("stimulus_rating", sa.Float()),
    ("rom_profile", sa.String()),
]

NUTRITION_LOG_COLUMNS = [
    ("verification_source", sa.String()),
    ("verified", sa.Boolean()),
    ("confidence", sa.String()),
    ("micros", sa.JSON()),
    ("items_breakdown", sa.JSON()),
]


def _existing_columns(conn, table: str) -> set:
    inspector = sa.inspect(conn)
    cols = inspector.get_columns(table)
    return {c["name"] for c in cols}


def _add_columns_if_missing(conn, table: str, columns: list[tuple] ):
    existing = _existing_columns(conn, table)
    for col_name, col_type in columns:
        if col_name in existing:
            continue
        op.add_column(table, sa.Column(col_name, col_type, nullable=True))


def upgrade() -> None:
    conn = op.get_bind()
    tables = {t for t in sa.inspect(conn).get_table_names()}
    if "food_items" in tables:
        _add_columns_if_missing(conn, "food_items", FOOD_MICRO_COLUMNS)
    if "exercise_library_items" in tables:
        _add_columns_if_missing(conn, "exercise_library_items", EXERCISE_COLUMNS)
    if "nutrition_logs" in tables:
        _add_columns_if_missing(conn, "nutrition_logs", NUTRITION_LOG_COLUMNS)

    if "evidence_topics" not in tables:
        op.create_table(
            "evidence_topics",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("topic", sa.String(), nullable=False, index=True),
            sa.Column("question_keywords", sa.String(), default="", index=True),
            sa.Column("muscle_group", sa.String(), nullable=True, index=True),
            sa.Column("focused_exercises", sa.String(), default=""),
            sa.Column("direct_answer", sa.Text(), nullable=False),
            sa.Column("biomechanics", sa.Text(), nullable=True),
            sa.Column("exercise_recommendations", sa.JSON(), nullable=True),
            sa.Column("key_studies", sa.JSON(), nullable=True),
            sa.Column("source_note", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), default=True, index=True),
            sa.Column("priority", sa.Integer(), default=5),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )


def downgrade() -> None:
    conn = op.get_bind()
    tables = {t for t in sa.inspect(conn).get_table_names()}
    if "evidence_topics" in tables:
        op.drop_table("evidence_topics")
    for table, columns in (
        ("food_items", FOOD_MICRO_COLUMNS),
        ("exercise_library_items", EXERCISE_COLUMNS),
        ("nutrition_logs", NUTRITION_LOG_COLUMNS),
    ):
        if table not in tables:
            continue
        existing = _existing_columns(conn, table)
        for col_name, _ in columns:
            if col_name in existing:
                try:
                    op.drop_column(table, col_name)
                except Exception:
                    pass