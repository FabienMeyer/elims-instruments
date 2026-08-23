"""Create the initial asset tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create instruments, boards, and DUTs."""
    op.create_table(
        "instruments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_tag", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("maker", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("connection", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_tag"),
    )
    op.create_table(
        "boards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_tag", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("maker", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("connection", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_tag"),
    )
    op.create_table(
        "duts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_tag", sa.String(), nullable=False),
        sa.Column("project", sa.String(), nullable=False),
        sa.Column("corner", sa.String(), nullable=False),
        sa.Column("revision", sa.String(), nullable=False),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("lot_number", sa.String(), nullable=True),
        sa.Column("wafer_id", sa.String(), nullable=True),
        sa.Column("die_x", sa.Integer(), nullable=True),
        sa.Column("die_y", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_tag"),
    )


def downgrade() -> None:
    """Remove all asset tables."""
    op.drop_table("duts")
    op.drop_table("boards")
    op.drop_table("instruments")
