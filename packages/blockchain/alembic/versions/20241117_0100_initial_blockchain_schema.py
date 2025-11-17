"""Initial blockchain schema

Revision ID: 001_initial
Revises:
Create Date: 2025-11-17 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create blocks table
    op.create_table(
        'blocks',
        sa.Column('block_height', sa.BigInteger(), nullable=False),
        sa.Column('block_hash', sa.CHAR(length=64), nullable=False),
        sa.Column('previous_hash', sa.CHAR(length=64), nullable=False),
        sa.Column('timestamp', sa.BigInteger(), nullable=False),
        sa.Column('validator_id', sa.String(length=255), nullable=False),
        sa.Column('transaction_count', sa.Integer(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('block_height')
    )
    op.create_index('idx_blocks_height', 'blocks', ['block_height'])
    op.create_index(op.f('ix_blocks_block_hash'), 'blocks', ['block_hash'], unique=True)

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('tx_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tx_hash', sa.CHAR(length=64), nullable=False),
        sa.Column('block_height', sa.BigInteger(), nullable=False),
        sa.Column('aggregator_id', sa.String(length=255), nullable=False),
        sa.Column('batch_size', sa.Integer(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('tx_id'),
        sa.ForeignKeyConstraint(['block_height'], ['blocks.block_height'])
    )
    op.create_index('idx_tx_block', 'transactions', ['block_height'])
    op.create_index(op.f('ix_transactions_tx_hash'), 'transactions', ['tx_hash'], unique=True)

    # Create image_hashes table
    op.create_table(
        'image_hashes',
        sa.Column('image_hash', sa.CHAR(length=64), nullable=False),
        sa.Column('tx_id', sa.Integer(), nullable=False),
        sa.Column('block_height', sa.BigInteger(), nullable=False),
        sa.Column('timestamp', sa.BigInteger(), nullable=False),
        sa.Column('aggregator_id', sa.String(length=255), nullable=False),
        sa.Column('gps_hash', sa.CHAR(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('image_hash'),
        sa.ForeignKeyConstraint(['tx_id'], ['transactions.tx_id']),
        sa.ForeignKeyConstraint(['block_height'], ['blocks.block_height'])
    )
    op.create_index('idx_hashes_block', 'image_hashes', ['block_height'])
    op.create_index('idx_hashes_timestamp', 'image_hashes', ['timestamp'])
    op.create_index('idx_hashes_aggregator', 'image_hashes', ['aggregator_id'])

    # Create pending_submissions table
    op.create_table(
        'pending_submissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('image_hash', sa.CHAR(length=64), nullable=False),
        sa.Column('encrypted_token', sa.LargeBinary(), nullable=False),
        sa.Column('table_references', sa.ARRAY(sa.Integer()), nullable=False),
        sa.Column('key_indices', sa.ARRAY(sa.Integer()), nullable=False),
        sa.Column('timestamp', sa.BigInteger(), nullable=False),
        sa.Column('gps_hash', sa.CHAR(length=64), nullable=True),
        sa.Column('device_signature', sa.LargeBinary(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('sma_validated', sa.Boolean(), nullable=False),
        sa.Column('validation_attempted_at', sa.DateTime(), nullable=True),
        sa.Column('validation_result', sa.String(length=50), nullable=True),
        sa.Column('batched', sa.Boolean(), nullable=False),
        sa.Column('batched_at', sa.DateTime(), nullable=True),
        sa.Column('tx_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tx_id'], ['transactions.tx_id'])
    )
    op.create_index(op.f('ix_pending_submissions_image_hash'), 'pending_submissions', ['image_hash'])
    op.create_index('idx_pending_validated', 'pending_submissions', ['sma_validated'])
    op.create_index('idx_pending_batched', 'pending_submissions', ['batched'])
    op.create_index('idx_pending_status', 'pending_submissions', ['sma_validated', 'batched'])
    op.create_index(op.f('ix_pending_submissions_sma_validated'), 'pending_submissions', ['sma_validated'])

    # Create node_state table
    op.create_table(
        'node_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.String(length=255), nullable=False),
        sa.Column('current_block_height', sa.BigInteger(), nullable=False),
        sa.Column('total_hashes', sa.BigInteger(), nullable=False),
        sa.Column('genesis_hash', sa.CHAR(length=64), nullable=True),
        sa.Column('last_block_time', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('node_state')
    op.drop_table('pending_submissions')
    op.drop_table('image_hashes')
    op.drop_table('transactions')
    op.drop_table('blocks')
