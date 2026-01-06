"""Add validation retry fields to pending_submissions

Revision ID: add_validation_retry
Revises: 79d5e2ca3acd
Create Date: 2026-01-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_validation_retry'
down_revision = '79d5e2ca3acd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add validation retry tracking fields."""
    # Add new columns
    op.add_column('pending_submissions', sa.Column('validation_status', sa.String(50), nullable=False, server_default='pending_ma_validation'))
    op.add_column('pending_submissions', sa.Column('validation_retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('pending_submissions', sa.Column('validation_next_retry', sa.String(50), nullable=True))
    op.add_column('pending_submissions', sa.Column('camera_cert', sa.Text(), nullable=True))
    op.add_column('pending_submissions', sa.Column('device_signature', sa.LargeBinary(), nullable=True))
    op.add_column('pending_submissions', sa.Column('blockchain_posted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('pending_submissions', sa.Column('block_number', sa.BigInteger(), nullable=True))

    # Create indexes
    op.create_index('idx_pending_validation_status', 'pending_submissions', ['validation_status'])
    op.create_index('idx_pending_blockchain_posted', 'pending_submissions', ['blockchain_posted'])


def downgrade() -> None:
    """Remove validation retry tracking fields."""
    # Drop indexes
    op.drop_index('idx_pending_blockchain_posted', 'pending_submissions')
    op.drop_index('idx_pending_validation_status', 'pending_submissions')

    # Drop columns
    op.drop_column('pending_submissions', 'block_number')
    op.drop_column('pending_submissions', 'blockchain_posted')
    op.drop_column('pending_submissions', 'device_signature')
    op.drop_column('pending_submissions', 'camera_cert')
    op.drop_column('pending_submissions', 'validation_next_retry')
    op.drop_column('pending_submissions', 'validation_retry_count')
    op.drop_column('pending_submissions', 'validation_status')
