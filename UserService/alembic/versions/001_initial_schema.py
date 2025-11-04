"""Initial schema for users table

Revision ID: 001
Revises:
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table"""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('phone_number'),
        sa.UniqueConstraint('username')
    )

    # Create indexes for better query performance
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_phone_number', 'users', ['phone_number'])
    op.create_index('ix_users_username', 'users', ['username'])


def downgrade() -> None:
    """Drop users table"""
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_phone_number', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
