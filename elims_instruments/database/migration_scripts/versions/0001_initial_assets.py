"""Create the initial ELIMS Instruments database schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create assets, projects, and their relationships."""
    op.create_table(
        "instruments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_tag", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("maker", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("calibration_date", sa.Date(), nullable=True),
        sa.Column("calibration_due_date", sa.Date(), nullable=True),
        sa.Column("calibration_certificate_number", sa.String(), nullable=True),
        sa.Column("calibration_status", sa.String(), nullable=False),
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
        "instrument_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.String(), nullable=False),
        sa.Column("asset_tag", sa.String(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_instrument_revisions_instrument_id"),
        "instrument_revisions",
        ["instrument_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_instrument_revisions_asset_tag"),
        "instrument_revisions",
        ["asset_tag"],
        unique=False,
    )
    op.create_index(
        op.f("ix_instrument_revisions_recorded_at"),
        "instrument_revisions",
        ["recorded_at"],
        unique=False,
    )
    op.create_table(
        "duts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_tag", sa.String(), nullable=False),
        sa.Column("project", sa.String(), nullable=False),
        sa.Column("corner", sa.String(), nullable=False),
        sa.Column("die_revision", sa.String(), nullable=False),
        sa.Column("metal_revision", sa.Integer(), nullable=True),
        sa.Column("package_revision", sa.String(), nullable=True),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("lot_number", sa.String(), nullable=True),
        sa.Column("wafer_id", sa.String(), nullable=True),
        sa.Column("die_x", sa.Integer(), nullable=True),
        sa.Column("die_y", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_tag"),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("internal_name", sa.String(), nullable=False),
        sa.Column("datasheet_name", sa.String(), nullable=False),
        sa.Column("specifications", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_projects_internal_name"),
        "projects",
        ["internal_name"],
        unique=True,
    )
    op.create_table(
        "project_supported_duts",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("dut_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["dut_id"], ["duts.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("project_id", "dut_id"),
    )
    op.create_table(
        "project_supported_boards",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("board_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["boards.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("project_id", "board_id"),
    )


def downgrade() -> None:
    """Remove the complete initial schema."""
    op.drop_table("project_supported_boards")
    op.drop_table("project_supported_duts")
    op.drop_index(op.f("ix_projects_internal_name"), table_name="projects")
    op.drop_table("projects")
    op.drop_table("duts")
    op.drop_index(
        op.f("ix_instrument_revisions_recorded_at"),
        table_name="instrument_revisions",
    )
    op.drop_index(
        op.f("ix_instrument_revisions_asset_tag"),
        table_name="instrument_revisions",
    )
    op.drop_index(
        op.f("ix_instrument_revisions_instrument_id"),
        table_name="instrument_revisions",
    )
    op.drop_table("instrument_revisions")
    op.drop_table("boards")
    op.drop_table("instruments")
