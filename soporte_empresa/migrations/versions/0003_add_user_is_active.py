"""add is_active column to user

Revision ID: 0003_add_user_is_active
Revises: 0002_ticket_options_catalog
Create Date: 2026-03-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_user_is_active'
down_revision = '0002_ticket_options_catalog'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column['name'] for column in inspector.get_columns('user')}

    if 'is_active' not in existing_columns:
        op.add_column('user', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column['name'] for column in inspector.get_columns('user')}

    if 'is_active' in existing_columns:
        op.drop_column('user', 'is_active')
