"""Besin ad eşleşmesi güven skoru."""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "f5a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e4f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {c["name"] for c in sa.inspect(conn).get_columns("food_items")}
    if "match_score" not in columns:
        op.add_column("food_items", sa.Column("match_score", sa.Float(), nullable=True))
        op.create_index("ix_food_items_match_score", "food_items", ["match_score"])


def downgrade() -> None:
    conn = op.get_bind()
    columns = {c["name"] for c in sa.inspect(conn).get_columns("food_items")}
    if "match_score" in columns:
        op.drop_index("ix_food_items_match_score", table_name="food_items")
        op.drop_column("food_items", "match_score")
