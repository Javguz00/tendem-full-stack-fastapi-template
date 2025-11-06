"""add event and event_participant tables

Revision ID: 7f8e9d0c1b2a
Revises: 1a31ce608336
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7f8e9d0c1b2a'
down_revision = '1a31ce608336'
branch_labels = None
depends_on = None


def upgrade():
    # Create event table
    op.create_table('event',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('event_time', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_event_owner_id'), 'event', ['owner_id'], unique=False)

    # Create event_participant junction table
    op.create_table('event_participant',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['event.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('event_id', 'user_id')
    )


def downgrade():
    # Drop tables in reverse order (to handle foreign key dependencies)
    op.drop_table('event_participant')
    op.drop_index(op.f('ix_event_owner_id'), table_name='event')
    op.drop_table('event')
