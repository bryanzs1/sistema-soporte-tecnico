"""add ticket options catalog

Revision ID: 0002_ticket_options_catalog
Revises: 0001_add_creator_name
Create Date: 2026-02-28 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_ticket_options_catalog'
down_revision = '0001_add_creator_name'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'ticket_option' not in existing_tables:
        op.create_table(
            'ticket_option',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('option_type', sa.String(length=20), nullable=False),
            sa.Column('value', sa.String(length=64), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('option_type', 'value', name='uq_ticket_option_type_value')
        )

    ticket_option = sa.table(
        'ticket_option',
        sa.column('option_type', sa.String),
        sa.column('value', sa.String),
        sa.column('active', sa.Boolean),
    )

    defaults = [
        {'option_type': 'category', 'value': 'Red', 'active': True},
        {'option_type': 'category', 'value': 'Impresoras', 'active': True},
        {'option_type': 'category', 'value': 'Software', 'active': True},
        {'option_type': 'category', 'value': 'Hardware', 'active': True},
        {'option_type': 'priority', 'value': 'Baja', 'active': True},
        {'option_type': 'priority', 'value': 'Media', 'active': True},
        {'option_type': 'priority', 'value': 'Alta', 'active': True},
        {'option_type': 'priority', 'value': 'Crítica', 'active': True},
    ]

    if 'ticket_option' in set(inspector.get_table_names()):
        for row in defaults:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO ticket_option (option_type, value, active)
                    VALUES (:option_type, :value, :active)
                    ON CONFLICT (option_type, value) DO NOTHING
                    """
                ),
                row
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'ticket_option' in set(inspector.get_table_names()):
        op.drop_table('ticket_option')
