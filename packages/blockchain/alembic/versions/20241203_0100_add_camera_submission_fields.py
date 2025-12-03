"""Add camera submission fields for 2-hash model

Revision ID: 002_camera_submission
Revises: 001_initial
Create Date: 2025-12-03 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_camera_submission'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add fields to support new camera submission format."""

    # Add new fields to pending_submissions table
    op.add_column('pending_submissions',
        sa.Column('modification_level', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('pending_submissions',
        sa.Column('parent_image_hash', sa.CHAR(64), nullable=True))
    op.add_column('pending_submissions',
        sa.Column('transaction_id', sa.String(36), nullable=True))
    op.add_column('pending_submissions',
        sa.Column('manufacturer_authority_id', sa.String(100), nullable=True))
    op.add_column('pending_submissions',
        sa.Column('camera_token_json', sa.Text(), nullable=True))

    # Create index on transaction_id for grouping 2-hash submissions
    op.create_index('idx_transaction_id', 'pending_submissions', ['transaction_id'])

    # Create index on modification_level for queries
    op.create_index('idx_modification_level', 'pending_submissions', ['modification_level'])

    # Create index on parent_image_hash for provenance chain queries
    op.create_index('idx_parent_hash', 'pending_submissions', ['parent_image_hash'])

    # Backfill existing records with defaults
    op.execute("""
        UPDATE pending_submissions
        SET modification_level = 0
        WHERE modification_level IS NULL
    """)

    # Make modification_level NOT NULL after backfill
    op.alter_column('pending_submissions', 'modification_level',
        existing_type=sa.Integer(),
        nullable=False,
        server_default=None)


def downgrade() -> None:
    """Remove camera submission fields."""

    # Drop indexes
    op.drop_index('idx_parent_hash', 'pending_submissions')
    op.drop_index('idx_modification_level', 'pending_submissions')
    op.drop_index('idx_transaction_id', 'pending_submissions')

    # Drop columns
    op.drop_column('pending_submissions', 'camera_token_json')
    op.drop_column('pending_submissions', 'manufacturer_authority_id')
    op.drop_column('pending_submissions', 'transaction_id')
    op.drop_column('pending_submissions', 'parent_image_hash')
    op.drop_column('pending_submissions', 'modification_level')
