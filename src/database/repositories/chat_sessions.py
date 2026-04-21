"""
Agentic Investment OS — Репозиторий ChatGPT Web Chat Sessions
Хранение ID/URL чатов для каждого агента в PostgreSQL.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.database.models import WebChatSession


class ChatSessionRepository:
    """Репозиторий для работы с таблицей `web_chat_sessions`."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_session(self, agent_name: str) -> Optional[WebChatSession]:
        """
        Получить сессию чата по имени агента.
        Возвращает None, если чат для агента ещё не создан.
        """
        result = await self.session.execute(
            select(WebChatSession).where(WebChatSession.agent_name == agent_name)
        )
        return result.scalar_one_or_none()

    async def save_session(self, agent_name: str, chat_url: str) -> WebChatSession:
        """
        Сохранить или обновить URL чата для агента.
        Используем upsert-логику: если запись есть — обновляем, нет — создаём.
        """
        existing = await self.get_session(agent_name)

        if existing:
            logger.info(f"🔄 Обновляем URL чата агента [{agent_name}]")
            await self.session.execute(
                update(WebChatSession)
                .where(WebChatSession.agent_name == agent_name)
                .values(
                    chat_url=chat_url,
                    last_used_at=datetime.utcnow(),
                )
            )
            await self.session.commit()
            # Перечитываем обновлённую запись
            return await self.get_session(agent_name)
        else:
            logger.info(f"🆕 Создаём запись чата для агента [{agent_name}]")
            record = WebChatSession(
                id=uuid.uuid4(),
                agent_name=agent_name,
                chat_url=chat_url,
            )
            self.session.add(record)
            await self.session.commit()
            await self.session.refresh(record)
            return record

    async def touch(self, agent_name: str) -> None:
        """Обновить метку `last_used_at` после успешного использования чата."""
        await self.session.execute(
            update(WebChatSession)
            .where(WebChatSession.agent_name == agent_name)
            .values(last_used_at=datetime.utcnow())
        )
        await self.session.commit()

    async def get_all_sessions(self) -> list[WebChatSession]:
        """Получить все хранимые сессии (для дебага/UI)."""
        result = await self.session.execute(select(WebChatSession))
        return list(result.scalars().all())

    async def delete_session(self, agent_name: str) -> None:
        """Удалить запись сессии (для пересоздания чата)."""
        existing = await self.get_session(agent_name)
        if existing:
            await self.session.delete(existing)
            await self.session.commit()
            logger.info(f"🗑️ Сессия агента [{agent_name}] удалена")
