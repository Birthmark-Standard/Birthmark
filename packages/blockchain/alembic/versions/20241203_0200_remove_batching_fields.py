"""Remove batching fields (no longer needed with custom blockchain)

Revision ID: 20241203_0200
Revises: 20241203_0100
Create Date: 2024-12-03 20:00:00.000000

Architecture Change:
- Original design: Batch hashes to reduce gas fees on public blockchain
- New design: Custom Birthmark blockchain with no gas fees
- Direct hash submission: Each hash submitted individually after validation
- No batching needed: Simpler verification for end users

Changes:
- Remove 'batched' field (no longer tracking batch status)
- Remove 'batched_at' field (no longer tracking batch time)
- Remove 'idx_pending_batched' index
- Remove 'idx_pending_status' composite index (sma_validated, batched)
- Keep 'tx_id' field (renamed purpose: tracks blockchain submission for crash recovery)

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241203_0200'
down_revision = '20241203_0100'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove batching fields - direct blockchain submission replaces batching."""

    # Drop indexes first
    op.drop_index('idx_pending_batched', table_name='pending_submissions')
    op.drop_index('idx_pending_status', table_name='pending_submissions')

    # Drop batching columns
    op.drop_column('pending_submissions', 'batched')
    op.drop_column('pending_submissions', 'batched_at')

    # Note: Keep tx_id column - now tracks blockchain submission state (not batch)
    # tx_id references transactions table for crash recovery during blockchain submission


def downgrade() -> None:
    """Restore batching fields (for rollback only)."""

    # Restore batching columns
    op.add_column('pending_submissions',
        sa.Column('batched', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('pending_submissions',
        sa.Column('batched_at', sa.DateTime(), nullable=True))

    # Restore indexes
    op.create_index('idx_pending_batched', 'pending_submissions', ['batched'])
    op.create_index('idx_pending_status', 'pending_submissions', ['sma_validated', 'batched'])
