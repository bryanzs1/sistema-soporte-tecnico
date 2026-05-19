"""add ticket table layout preferences to user

Revision ID: 0005_ticket_table_layout
Revises: 0004_add_user_last_activity
Create Date: 2026-03-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005_ticket_table_layout'
down_revision = '0004_add_user_last_activity'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column['name'] for column in inspector.get_columns('user')}

    if 'ticket_table_layout' not in existing_columns:
        op.add_column('user', sa.Column('ticket_table_layout', sa.Text(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column['name'] for column in inspector.get_columns('user')}

    if 'ticket_table_layout' in existing_columns:
        op.drop_column('user', 'ticket_table_layout')
