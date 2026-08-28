"""user_profile tablosuna izin/plan kolonlari ekle

Revision ID: a1f2c3d4e5b6
Revises: eb95af9d1758
Create Date: 2026-08-28

models.UserProfile uzerinde tanimli olan ama ilk migration'da bulunmayan
3 kolonu (camera_permission_granted, microphone_permission_granted,
preferred_plan) ekler. Bu kolonlar eksikken /api/status ve profil
uclari "no such column" hatasiyla dusuyordu.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1f2c3d4e5b6'
down_revision: Union[str, Sequence[str], None] = 'eb95af9d1758'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS_TO_ADD = [
    ("camera_permission_granted", sa.Boolean(), False),
    ("microphone_permission_granted", sa.Boolean(), False),
    ("preferred_plan", sa.String(), "FREE"),
]


def _existing_columns(conn) -> set:
    inspector = sa.inspect(conn)
    if not inspector.has_table("user_profile"):
        return set()
    return {c["name"] for c in inspector.get_columns("user_profile")}


def upgrade() -> None:
    conn = op.get_bind()
    existing = _existing_columns(conn)
    if not existing:
        # Tablo hic yoksa (sifirdan kurulum) bir sey yapma; initial schema olusturur.
        return
    for name, col_type, default in COLUMNS_TO_ADD:
        if name not in existing:
            op.add_column(
                "user_profile",
                sa.Column(name, col_type, nullable=True, server_default=sa.text(f"'{default}'") if isinstance(default, str) else sa.text(str(int(default)))),
            )


def downgrade() -> None:
    conn = op.get_bind()
    existing = _existing_columns(conn)
    for name, _, _ in COLUMNS_TO_ADD:
        if name in existing:
            op.drop_column("user_profile", name)
