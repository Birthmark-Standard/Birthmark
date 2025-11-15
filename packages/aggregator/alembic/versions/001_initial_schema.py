"""Initial schema with submissions, batches, merkle_proofs, SMA and SSA tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-11-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create submissions table
    op.create_table(
        'submissions',
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('submission_type', sa.String(length=10), nullable=False),
        sa.Column('image_hash', sa.String(length=64), nullable=False),
        sa.Column('modification_level', sa.Integer(), nullable=False),
        sa.Column('parent_image_hash', sa.String(length=64), nullable=True),
        sa.Column('camera_token_ciphertext', sa.Text(), nullable=True),
        sa.Column('camera_token_auth_tag', sa.String(length=32), nullable=True),
        sa.Column('camera_token_nonce', sa.String(length=24), nullable=True),
        sa.Column('table_id', sa.Integer(), nullable=True),
        sa.Column('key_index', sa.Integer(), nullable=True),
        sa.Column('manufacturer_authority_id', sa.String(length=100), nullable=True),
        sa.Column('manufacturer_validation_endpoint', sa.Text(), nullable=True),
        sa.Column('program_token', sa.String(length=64), nullable=True),
        sa.Column('developer_authority_id', sa.String(length=100), nullable=True),
        sa.Column('developer_version_string', sa.String(length=200), nullable=True),
        sa.Column('developer_validation_endpoint', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.BigInteger(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('validation_status', sa.String(length=20), nullable=False),
        sa.Column('validation_error', sa.Text(), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("submission_type IN ('camera', 'software')", name='check_submission_type'),
        sa.CheckConstraint('modification_level >= 0 AND modification_level <= 2', name='check_modification_level'),
        sa.CheckConstraint('table_id IS NULL OR (table_id >= 0 AND table_id < 250)', name='check_table_id'),
        sa.CheckConstraint('key_index IS NULL OR (key_index >= 0 AND key_index < 1000)', name='check_key_index'),
        sa.PrimaryKeyConstraint('submission_id')
    )
    op.create_index(op.f('ix_submissions_batch_id'), 'submissions', ['batch_id'], unique=False)
    op.create_index(op.f('ix_submissions_image_hash'), 'submissions', ['image_hash'], unique=False)
    op.create_index(op.f('ix_submissions_modification_level'), 'submissions', ['modification_level'], unique=False)
    op.create_index(op.f('ix_submissions_parent_image_hash'), 'submissions', ['parent_image_hash'], unique=False)
    op.create_index(op.f('ix_submissions_submission_type'), 'submissions', ['submission_type'], unique=False)
    op.create_index(op.f('ix_submissions_transaction_id'), 'submissions', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_submissions_validation_status'), 'submissions', ['validation_status'], unique=False)

    # Create batches table
    op.create_table(
        'batches',
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('image_count', sa.Integer(), nullable=False),
        sa.Column('merkle_root', sa.String(length=64), nullable=False),
        sa.Column('tree_depth', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('zksync_tx_hash', sa.String(length=66), nullable=True),
        sa.Column('zksync_block_number', sa.BigInteger(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'merkle_complete', 'posted', 'finalized')", name='check_batch_status'),
        sa.PrimaryKeyConstraint('batch_id'),
        sa.UniqueConstraint('merkle_root')
    )
    op.create_index(op.f('ix_batches_created_at'), 'batches', ['created_at'], unique=False)
    op.create_index(op.f('ix_batches_merkle_root'), 'batches', ['merkle_root'], unique=False)
    op.create_index(op.f('ix_batches_status'), 'batches', ['status'], unique=False)

    # Create merkle_proofs table
    op.create_table(
        'merkle_proofs',
        sa.Column('proof_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_hash', sa.String(length=64), nullable=False),
        sa.Column('leaf_index', sa.Integer(), nullable=False),
        sa.Column('proof_path', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('proof_id'),
        sa.UniqueConstraint('batch_id', 'image_hash', name='uq_batch_image')
    )
    op.create_index('idx_merkle_proof_batch_id', 'merkle_proofs', ['batch_id'], unique=False)
    op.create_index('idx_merkle_proof_image_hash', 'merkle_proofs', ['image_hash'], unique=False)
    op.create_index(op.f('ix_merkle_proofs_batch_id'), 'merkle_proofs', ['batch_id'], unique=False)
    op.create_index(op.f('ix_merkle_proofs_image_hash'), 'merkle_proofs', ['image_hash'], unique=False)

    # Create SMA tables
    op.create_table(
        'sma_cameras',
        sa.Column('camera_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('camera_serial', sa.String(length=100), nullable=False),
        sa.Column('manufacturer', sa.String(length=50), nullable=False),
        sa.Column('nuc_hash', sa.String(length=64), nullable=False),
        sa.Column('table_ids', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('provisioned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('camera_id'),
        sa.UniqueConstraint('camera_serial'),
        sa.UniqueConstraint('nuc_hash')
    )
    op.create_index(op.f('ix_sma_cameras_nuc_hash'), 'sma_cameras', ['nuc_hash'], unique=False)

    op.create_table(
        'sma_key_tables',
        sa.Column('table_id', sa.Integer(), nullable=False),
        sa.Column('master_key', sa.String(length=64), nullable=False),
        sa.CheckConstraint('table_id >= 0 AND table_id < 250', name='check_sma_table_id'),
        sa.PrimaryKeyConstraint('table_id')
    )

    # Create SSA tables
    op.create_table(
        'ssa_software',
        sa.Column('software_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('authority_id', sa.String(length=100), nullable=False),
        sa.Column('developer_name', sa.String(length=100), nullable=False),
        sa.Column('software_name', sa.String(length=100), nullable=False),
        sa.Column('program_hash', sa.String(length=64), nullable=False),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('software_id'),
        sa.UniqueConstraint('authority_id')
    )
    op.create_index(op.f('ix_ssa_software_authority_id'), 'ssa_software', ['authority_id'], unique=False)

    op.create_table(
        'ssa_software_versions',
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('software_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_string', sa.String(length=200), nullable=False),
        sa.Column('expected_token', sa.String(length=64), nullable=False),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('version_id'),
        sa.UniqueConstraint('software_id', 'version_string', name='uq_software_version')
    )
    op.create_index(op.f('ix_ssa_software_versions_software_id'), 'ssa_software_versions', ['software_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('ssa_software_versions')
    op.drop_table('ssa_software')
    op.drop_table('sma_key_tables')
    op.drop_table('sma_cameras')
    op.drop_table('merkle_proofs')
    op.drop_table('batches')
    op.drop_table('submissions')
