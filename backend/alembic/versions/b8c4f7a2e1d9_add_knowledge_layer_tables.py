"""knowledge layer tablolari: food_items, exercise_library_items, research_notes

Revision ID: b8c4f7a2e1d9
Revises: a1f2c3d4e5b6
Create Date: 2026-09-10

Bilgi katmani (knowledge layer) guncellemesinin 3 yeni tablosu. Kullanicidan
bagimsiz (global) kutuphanelerdir: USDA besin verisi, kanonik egzersiz
kutuphanesi ve kuretorlu bilimsel bulgu notlari. Tablo zaten varsa (ornek:
Bale create_all ile olusmus SQLite) idempotent davranir - bir sey yapmaz.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b8c4f7a2e1d9'
down_revision: Union[str, Sequence[str], None] = 'a1f2c3d4e5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    (
        "food_items",
        [
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("aliases", sa.String(), nullable=True),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("calories_per_100g", sa.Float(), nullable=True),
            sa.Column("protein_per_100g", sa.Float(), nullable=True),
            sa.Column("carbs_per_100g", sa.Float(), nullable=True),
            sa.Column("fats_per_100g", sa.Float(), nullable=True),
            sa.Column("fiber_per_100g", sa.Float(), nullable=True),
            sa.Column("typical_portion_g", sa.Integer(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("usda_fdc_id", sa.Integer(), nullable=True),
            sa.Column("dietary_tags", sa.String(), nullable=True),
            sa.Column("pending_review", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        ],
        [("ix_food_items_id", ["id"]), ("ix_food_items_name", ["name"]), ("ix_food_items_category", ["category"]), ("ix_food_items_source", ["source"]), ("ix_food_items_pending_review", ["pending_review"]), ("ix_food_items_usda_fdc_id", ["usda_fdc_id"])],
    ),
    (
        "exercise_library_items",
        [
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("aliases", sa.String(), nullable=True),
            sa.Column("muscle_group", sa.String(), nullable=False),
            sa.Column("secondary_muscles", sa.String(), nullable=True),
            sa.Column("exercise_type", sa.String(), nullable=True),
            sa.Column("stretch_mediated", sa.Boolean(), nullable=True),
            sa.Column("unilateral", sa.Boolean(), nullable=True),
            sa.Column("equipment", sa.String(), nullable=True),
            sa.Column("technique_cue", sa.Text(), nullable=True),
            sa.Column("rep_range_bias", sa.String(), nullable=True),
            sa.Column("contraindications", sa.String(), nullable=True),
            sa.Column("evidence_refs", sa.String(), nullable=True),
            sa.Column("selection_reason", sa.Text(), nullable=True),
            sa.Column("pending_review", sa.Boolean(), nullable=True),
            sa.Column("usage_count", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        ],
        [("ix_exercise_library_items_id", ["id"]), ("ix_exercise_library_items_name", ["name"]), ("ix_exercise_library_items_muscle_group", ["muscle_group"]), ("ix_exercise_library_items_equipment", ["equipment"]), ("ix_exercise_library_items_pending_review", ["pending_review"])],
    ),
    (
        "research_notes",
        [
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("topic", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("finding_rule", sa.Text(), nullable=True),
            sa.Column("evidence_refs", sa.String(), nullable=True),
            sa.Column("source_type", sa.String(), nullable=True),
            sa.Column("target_muscle_group", sa.String(), nullable=True),
            sa.Column("relevance_score", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        ],
        [("ix_research_notes_id", ["id"]), ("ix_research_notes_topic", ["topic"]), ("ix_research_notes_source_type", ["source_type"]), ("ix_research_notes_target_muscle_group", ["target_muscle_group"]), ("ix_research_notes_is_active", ["is_active"])],
    ),
]


def _existing_tables(conn) -> set:
    inspector = sa.inspect(conn)
    return set(inspector.get_table_names())


def upgrade() -> None:
    conn = op.get_bind()
    existing = _existing_tables(conn)
    for table_name, columns, indexes in TABLES:
        if table_name in existing:
            continue  # idempotent: tablo zaten varsa dokunma
        op.create_table(table_name, *columns)
        for index_name, index_cols in indexes:
            op.create_index(op.f(index_name), table_name, index_cols)


def downgrade() -> None:
    conn = op.get_bind()
    existing = _existing_tables(conn)
    for table_name, _, _ in reversed(TABLES):
        if table_name in existing:
            op.drop_table(table_name)