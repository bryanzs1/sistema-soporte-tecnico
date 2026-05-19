"""
Script de migración Alembic para Stripe Billing en Company y tabla BillingEvent
Generado por GitHub Copilot el 18/04/2026
"""

# Alembic identifiers
revision = '20260418_add_stripe_billing'
down_revision = '0006_add_company_multiempresa'
branch_labels = None
depends_on = None
from alembic import op
import sqlalchemy as sa
from datetime import datetime


def _inspector():
    return sa.inspect(op.get_bind())


def _has_column(table_name, column_name):
    inspector = _inspector()
    return any(column['name'] == column_name for column in inspector.get_columns(table_name))

def upgrade():
    if not _has_column('company', 'billing_status'):
        op.add_column('company', sa.Column('billing_status', sa.String(length=32), nullable=False, server_default='inactive'))

    if not _has_column('company', 'stripe_customer_id'):
        op.add_column('company', sa.Column('stripe_customer_id', sa.String(length=64)))

    if not _has_column('company', 'stripe_subscription_id'):
        op.add_column('company', sa.Column('stripe_subscription_id', sa.String(length=64)))

    if not _has_column('company', 'stripe_price_id'):
        op.add_column('company', sa.Column('stripe_price_id', sa.String(length=64)))

    if not _has_column('company', 'stripe_current_period_end'):
        op.add_column('company', sa.Column('stripe_current_period_end', sa.DateTime()))

    if not _has_column('company', 'stripe_cancel_at_period_end'):
        op.add_column('company', sa.Column('stripe_cancel_at_period_end', sa.Boolean(), server_default=sa.text('false')))

    if not _has_column('company', 'stripe_last_invoice_url'):
        op.add_column('company', sa.Column('stripe_last_invoice_url', sa.String(length=255)))

    if not _has_column('company', 'stripe_last_payment'):
        op.add_column('company', sa.Column('stripe_last_payment', sa.DateTime()))

    if not _inspector().has_table('billing_event'):
        op.create_table(
            'billing_event',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('company_id', sa.Integer, sa.ForeignKey('company.id'), nullable=False, index=True),
            sa.Column('event_type', sa.String(length=64), nullable=False),
            sa.Column('event_id', sa.String(length=128), nullable=False, unique=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
            sa.Column('data', sa.Text),
        )

def downgrade():
    if _inspector().has_table('billing_event'):
        op.drop_table('billing_event')

    if _has_column('company', 'billing_status'):
        op.drop_column('company', 'billing_status')

    if _has_column('company', 'stripe_customer_id'):
        op.drop_column('company', 'stripe_customer_id')

    if _has_column('company', 'stripe_subscription_id'):
        op.drop_column('company', 'stripe_subscription_id')

    if _has_column('company', 'stripe_price_id'):
        op.drop_column('company', 'stripe_price_id')

    if _has_column('company', 'stripe_current_period_end'):
        op.drop_column('company', 'stripe_current_period_end')

    if _has_column('company', 'stripe_cancel_at_period_end'):
        op.drop_column('company', 'stripe_cancel_at_period_end')

    if _has_column('company', 'stripe_last_invoice_url'):
        op.drop_column('company', 'stripe_last_invoice_url')

    if _has_column('company', 'stripe_last_payment'):
        op.drop_column('company', 'stripe_last_payment')
