"""Add client bot tables

Revision ID: 001
Revises:
Create Date: 2026-01-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # bot_users
    op.create_table(
        'bot_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('audits_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('audits_reset_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )

    # leads
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('contact_method', sa.String(length=50), nullable=True),
        sa.Column('sku_count', sa.String(length=50), nullable=True),
        sa.Column('urgency', sa.String(length=50), nullable=True),
        sa.Column('marketplaces', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('task', sa.Text(), nullable=True),
        sa.Column('budget', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='new'),
        sa.Column('bot_activity', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['bot_users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # conversations
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('messages', postgresql.JSON(), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['bot_users.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('conversations')
    op.drop_table('leads')
    op.drop_table('bot_users')
