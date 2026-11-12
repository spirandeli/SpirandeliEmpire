"""Initial and complete SpirandeliEmpire OS 3.1 schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from app.database.session import Base
import app.database.models  # noqa: F401

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Create any missing tables from SQLAlchemy metadata (works on fresh & existing DBs)
    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(Base.metadata.sorted_tables):
        table.drop(bind=bind, checkfirst=True)

