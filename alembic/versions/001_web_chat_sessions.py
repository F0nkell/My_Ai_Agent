"""add web_chat_sessions table

Revision ID: 001_web_chat_sessions
Revises: 
Create Date: 2026-04-21

Добавляет таблицу web_chat_sessions для хранения URL чатов агентов на ChatGPT Plus.
Один чат на агента. URL сохраняется безвозвратно при первом создании чата.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_web_chat_sessions'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'web_chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_name', sa.String(50), nullable=False),
        sa.Column('chat_url', sa.String(500), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_name', name='uq_web_chat_sessions_agent_name'),
    )
    op.create_index(
        'ix_web_chat_sessions_agent',
        'web_chat_sessions',
        ['agent_name'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_web_chat_sessions_agent', table_name='web_chat_sessions')
    op.drop_table('web_chat_sessions')
