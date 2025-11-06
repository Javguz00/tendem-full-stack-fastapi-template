"""create user table (base migration)

Revision ID: 1a31ce608336
Revises: 
Create Date: 2025-11-06 15:05:00.000000

This migration creates the `user` table which other revisions depend on.
If you already have a prior migration that created users, prefer restoring
that file instead of using this synthetic base migration.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1a31ce608336'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create user table
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('full_name', sa.String(length=255), nullable=True),
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
