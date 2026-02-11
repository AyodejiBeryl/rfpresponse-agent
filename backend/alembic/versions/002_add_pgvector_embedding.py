"""Add pgvector embedding column

Revision ID: 002
Revises: 001
Create Date: 2026-02-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding column to knowledge_chunks
    op.execute(
        "ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536)"
    )

    # Create IVFFlat index for cosine similarity search
    # Note: IVFFlat requires at least some data to build the index,
    # so we create it with a low list count suitable for small datasets
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding
        ON knowledge_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
