"""add creator_name column to ticket

Revision ID: 0001_add_creator_name
Revises: 
Create Date: 2026-02-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_creator_name'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column['name'] for column in inspector.get_columns('ticket')}

    if 'creator_name' not in existing_columns:
        op.add_column(
            'ticket',
            sa.Column('creator_name', sa.String(length=120), nullable=False, server_default='')
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column['name'] for column in inspector.get_columns('ticket')}

    if 'creator_name' in existing_columns:
        op.drop_column('ticket', 'creator_name')