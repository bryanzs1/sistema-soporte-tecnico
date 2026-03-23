"""add last_activity column to user

Revision ID: 0004_add_user_last_activity
Revises: 0003_add_user_is_active
Create Date: 2026-03-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_user_last_activity'
down_revision = '0003_add_user_is_active'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column['name'] for column in inspector.get_columns('user')}

    if 'last_activity' not in existing_columns:
        op.add_column('user', sa.Column('last_activity', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column['name'] for column in inspector.get_columns('user')}

    if 'last_activity' in existing_columns:
        op.drop_column('user', 'last_activity')
