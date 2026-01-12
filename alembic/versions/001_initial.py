"""Initial migration

Revision ID: 001
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('settings', postgresql.JSONB),
        sa.Column('subscription_tier', sa.String(50)),
        sa.Column('api_key_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
    )

def downgrade() -> None:
    op.drop_table('tenants')
