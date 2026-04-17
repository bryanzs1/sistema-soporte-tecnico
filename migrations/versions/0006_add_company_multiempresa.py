"""
Revision ID: 0006_add_company_multiempresa
Revises: 0005_add_user_ticket_table_layout
Create Date: 2026-04-17
"""

# --- Alembic identifiers ---
revision = '0006_add_company_multiempresa'
down_revision = '0005_ticket_table_layout'
branch_labels = None
depends_on = None
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. Crear tabla company
    op.create_table(
        'company',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False, unique=True),
        sa.Column('description', sa.String(length=255)),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    # 2. Agregar company_id a user
    op.add_column('user', sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=True))
    # 3. Agregar company_id a ticket
    op.add_column('ticket', sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=True))

    # 4. (Opcional) Crear empresa Soporte IT Pro y asociar usuarios/tickets existentes
    # Esto se puede hacer con un script de datos aparte si se requiere

def downgrade():
    op.drop_column('ticket', 'company_id')
    op.drop_column('user', 'company_id')
    op.drop_table('company')
