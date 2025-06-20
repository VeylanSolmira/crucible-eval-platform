"""Refactor output storage fields for clarity

Revision ID: ecb8af5d833a
Revises: 8f877d71a993
Create Date: 2025-06-19 22:11:42.262306

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ecb8af5d833a'
down_revision = '8f877d71a993'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename existing columns
    op.alter_column('evaluations', 'output_preview', new_column_name='output')
    op.alter_column('evaluations', 'error_preview', new_column_name='error')
    op.alter_column('evaluations', 'output_size_bytes', new_column_name='output_size')
    
    # Add new columns for truncation tracking
    op.add_column('evaluations', sa.Column('output_truncated', sa.Boolean(), nullable=True, default=False))
    op.add_column('evaluations', sa.Column('error_truncated', sa.Boolean(), nullable=True, default=False))
    op.add_column('evaluations', sa.Column('error_size', sa.BigInteger(), nullable=True))
    
    # Rename S3 columns to be more generic (could be any storage location)
    op.alter_column('evaluations', 'output_s3_key', new_column_name='output_location')
    op.alter_column('evaluations', 'error_s3_key', new_column_name='error_location')
    op.alter_column('evaluations', 'code_s3_key', new_column_name='code_location')
    
    # Set default values for new boolean columns
    op.execute("UPDATE evaluations SET output_truncated = FALSE WHERE output_truncated IS NULL")
    op.execute("UPDATE evaluations SET error_truncated = FALSE WHERE error_truncated IS NULL")


def downgrade() -> None:
    # Reverse the changes
    op.alter_column('evaluations', 'output', new_column_name='output_preview')
    op.alter_column('evaluations', 'error', new_column_name='error_preview')
    op.alter_column('evaluations', 'output_size', new_column_name='output_size_bytes')
    
    # Remove truncation columns
    op.drop_column('evaluations', 'output_truncated')
    op.drop_column('evaluations', 'error_truncated')
    op.drop_column('evaluations', 'error_size')
    
    # Rename location columns back to S3-specific names
    op.alter_column('evaluations', 'output_location', new_column_name='output_s3_key')
    op.alter_column('evaluations', 'error_location', new_column_name='error_s3_key')
    op.alter_column('evaluations', 'code_location', new_column_name='code_s3_key')