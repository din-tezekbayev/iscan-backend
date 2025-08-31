"""Add processing fields to FileType

Revision ID: 002_add_processing_fields
Revises: 001_initial_baseline
Create Date: 2025-08-31 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_processing_fields'
down_revision: Union[str, None] = '001_initial_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define enums
processing_mode_enum = postgresql.ENUM('IMAGE_OCR', 'TEXT_EXTRACTION', name='processingmode', create_type=False)
processor_type_enum = postgresql.ENUM('HUAWEI_ACT', 'INVOICE', 'CONTRACT', 'RECEIPT', 'CUSTOM', name='processortype', create_type=False)


def upgrade() -> None:
    # Create enum types
    processing_mode_enum.create(op.get_bind())
    processor_type_enum.create(op.get_bind())
    
    # Add new columns to file_types table
    op.add_column('file_types', sa.Column('processor_type', processor_type_enum, nullable=False, server_default='CUSTOM'))
    op.add_column('file_types', sa.Column('processing_mode', processing_mode_enum, nullable=False, server_default='IMAGE_OCR'))
    op.add_column('file_types', sa.Column('verification_enabled', sa.Boolean(), nullable=False, server_default='false'))
    
    # Update existing huawei record to use HUAWEI_ACT processor type
    op.execute("UPDATE file_types SET processor_type = 'HUAWEI_ACT', processing_mode = 'IMAGE_OCR', verification_enabled = true WHERE name = 'huawei'")


def downgrade() -> None:
    # Remove columns
    op.drop_column('file_types', 'verification_enabled')
    op.drop_column('file_types', 'processing_mode')
    op.drop_column('file_types', 'processor_type')
    
    # Drop enum types
    processor_type_enum.drop(op.get_bind())
    processing_mode_enum.drop(op.get_bind())