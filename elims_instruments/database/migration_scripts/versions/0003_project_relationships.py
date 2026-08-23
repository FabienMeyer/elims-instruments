"""Upgrade legacy project resource lists to relationships."""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _identifiers(value: object) -> list[str]:
    """Decode a legacy JSON identifier list."""
    decoded = json.loads(value) if isinstance(value, str) else value
    if not isinstance(decoded, list) or any(
        not isinstance(identifier, str) for identifier in decoded
    ):
        raise ValueError("Invalid legacy project resource list")
    return decoded


def _create_link_tables(existing_tables: set[str]) -> None:
    """Create relationship tables missing from a legacy revision 0002 schema."""
    if "project_supported_duts" not in existing_tables:
        op.create_table(
            "project_supported_duts",
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("dut_id", sa.String(), nullable=False),
            sa.ForeignKeyConstraint(["dut_id"], ["duts.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("project_id", "dut_id"),
        )
    if "project_supported_boards" not in existing_tables:
        op.create_table(
            "project_supported_boards",
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("board_id", sa.String(), nullable=False),
            sa.ForeignKeyConstraint(["board_id"], ["boards.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("project_id", "board_id"),
        )


def upgrade() -> None:
    """Convert legacy JSON lists when upgrading an existing revision 0002 DB."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    project_columns = {column["name"] for column in inspector.get_columns("projects")}
    if "supported_duts" not in project_columns:
        return

    _create_link_tables(set(inspector.get_table_names()))
    projects = connection.execute(
        sa.text("SELECT id, supported_duts, supported_boards FROM projects")
    ).mappings()
    for project in projects:
        project_id = project["id"]
        for identifier in set(_identifiers(project["supported_duts"])):
            dut_id = connection.execute(
                sa.text(
                    "SELECT id FROM duts "
                    "WHERE id = :identifier OR asset_tag = :identifier"
                ),
                {"identifier": identifier},
            ).scalar_one_or_none()
            if dut_id is None:
                raise ValueError(f"Supported DUT not found: {identifier}")
            connection.execute(
                sa.text(
                    "INSERT INTO project_supported_duts (project_id, dut_id) "
                    "VALUES (:project_id, :resource_id)"
                ),
                {"project_id": project_id, "resource_id": dut_id},
            )
        for identifier in set(_identifiers(project["supported_boards"])):
            board_id = connection.execute(
                sa.text(
                    "SELECT id FROM boards "
                    "WHERE id = :identifier OR asset_tag = :identifier"
                ),
                {"identifier": identifier},
            ).scalar_one_or_none()
            if board_id is None:
                raise ValueError(f"Supported board not found: {identifier}")
            connection.execute(
                sa.text(
                    "INSERT INTO project_supported_boards (project_id, board_id) "
                    "VALUES (:project_id, :resource_id)"
                ),
                {"project_id": project_id, "resource_id": board_id},
            )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("supported_boards")
        batch_op.drop_column("supported_duts")


def downgrade() -> None:
    """Revision 0002 already represents the relational schema for new DBs."""
