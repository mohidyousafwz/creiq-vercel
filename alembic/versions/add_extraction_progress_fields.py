"""Add extraction progress fields

Revision ID: add_extraction_progress
Revises: 
Create Date: 2024-01-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_extraction_progress'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to roll_numbers table
    op.add_column('roll_numbers', sa.Column('total_appeals_found', sa.Integer(), nullable=True))
    op.add_column('roll_numbers', sa.Column('appeals_extracted', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('roll_numbers', sa.Column('extraction_progress', sa.JSON(), nullable=True))


def downgrade():
    # Remove columns
    op.drop_column('roll_numbers', 'extraction_progress')
    op.drop_column('roll_numbers', 'appeals_extracted')
    op.drop_column('roll_numbers', 'total_appeals_found') 