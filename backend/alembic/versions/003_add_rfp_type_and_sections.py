"""Add rfp_type and detected_sections to projects table.

Revision ID: 003_add_rfp_type_and_sections
Revises: 002_add_pgvector_embedding
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '003_add_rfp_type_and_sections'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add rfp_type column to projects table
    op.add_column(
        'projects',
        sa.Column('rfp_type', sa.String(50), nullable=True)
    )

    # Add detected_sections column to projects table
    op.add_column(
        'projects',
        sa.Column('detected_sections', JSONB, nullable=True, server_default='[]')
    )

    # Create index on rfp_type for filtering
    op.create_index(
        'ix_projects_rfp_type',
        'projects',
        ['rfp_type']
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_projects_rfp_type', table_name='projects')

    # Drop columns
    op.drop_column('projects', 'detected_sections')
    op.drop_column('projects', 'rfp_type')
