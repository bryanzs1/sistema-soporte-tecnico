"""
Revision ID: 0006_add_company_multiempresa
Revises: 0005_add_user_ticket_table_layout
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa


revision = '0006_add_company_multiempresa'
down_revision = '0005_ticket_table_layout'
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name):
    return table_name in _inspector().get_table_names()


def _has_column(table_name, column_name):
    return any(column['name'] == column_name for column in _inspector().get_columns(table_name))


def _has_fk(table_name, fk_name):
    return any(fk.get('name') == fk_name for fk in _inspector().get_foreign_keys(table_name))


def upgrade():
    if not _has_table('company'):
        op.create_table(
            'company',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=120), nullable=False, unique=True),
            sa.Column('description', sa.String(length=255)),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_column('user', 'company_id'):
        with op.batch_alter_table('user') as batch_op:
            batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))

    if not _has_fk('user', 'fk_user_company_id_company'):
        with op.batch_alter_table('user') as batch_op:
            batch_op.create_foreign_key('fk_user_company_id_company', 'company', ['company_id'], ['id'])

    if not _has_column('ticket', 'company_id'):
        with op.batch_alter_table('ticket') as batch_op:
            batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))

    if not _has_fk('ticket', 'fk_ticket_company_id_company'):
        with op.batch_alter_table('ticket') as batch_op:
            batch_op.create_foreign_key('fk_ticket_company_id_company', 'company', ['company_id'], ['id'])


def downgrade():
    if _has_fk('ticket', 'fk_ticket_company_id_company'):
        with op.batch_alter_table('ticket') as batch_op:
            batch_op.drop_constraint('fk_ticket_company_id_company', type_='foreignkey')
    if _has_column('ticket', 'company_id'):
        with op.batch_alter_table('ticket') as batch_op:
            batch_op.drop_column('company_id')

    if _has_fk('user', 'fk_user_company_id_company'):
        with op.batch_alter_table('user') as batch_op:
            batch_op.drop_constraint('fk_user_company_id_company', type_='foreignkey')
    if _has_column('user', 'company_id'):
        with op.batch_alter_table('user') as batch_op:
            batch_op.drop_column('company_id')

    if _has_table('company'):
        op.drop_table('company')
