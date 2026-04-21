"""
Agentic Investment OS — Базовый агент (Playwright-версия)
Stateful логика: системный промпт отправляется ОДИН раз при создании чата.
Последующие вызовы только отправляют данные (user prompt).
"""

import hashlib
import json
import time
from typing import Optional, Type

from loguru import logger
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.browser_provider import BrowserProvider, get_browser_provider
from src.database.repositories.chat_sessions import ChatSessionRepository


class BaseAgent:
    """
    Базовый класс для всех агентов (Playwright / ChatGPT Plus Web).

    Логика:
    1. Первый вызов: создаём чат на chatgpt.com, отправляем системный промпт,
       сохраняем URL в БД.
    2. Последующие вызовы: переходим по сохранённому URL, отправляем только
       данные (user_prompt — новости / рыночные данные / итоги других агентов).
    3. Ответ парсится из JSON и валидируется через Pydantic.
    """

    # Переопределяем в дочерних классах
    name: str = "base_agent"
    system_prompt: str = ""         # Системный промпт (отправляется 1 раз при создании чата)
    output_schema: Optional[Type[BaseModel]] = None

    def __init__(self, db_session: AsyncSession = None):
        self.db_session = db_session
        self._chat_url: Optional[str] = None   # Кеш URL в памяти (актуален в рамках запуска)
        self._prompt_hash = hashlib.sha256(
            self.system_prompt.encode()
        ).hexdigest()[:16]

    async def run(self, context: dict, provider: BrowserProvider) -> dict:
        """
        Главный метод запуска агента.

        Args:
            context: Данные для анализа (новости, рыночные данные и т.д.)
            provider: Инициализированный BrowserProvider

        Returns:
            dict с полями: agent_name, output, confidence, latency_ms, model_used, prompt_hash
        """
        start_time = time.time()
        logger.info(f"🤖 Агент [{self.name}] запускается...")

        try:
            # Шаг 1: Гарантируем наличие чата
            chat_url = await self._ensure_chat_exists(provider)

            # Шаг 2: Формируем user_prompt с данными
            user_prompt = self._build_user_prompt(context)

            # Шаг 3: Отправляем данные и получаем ответ
            raw_response = await provider.send_message(chat_url, user_prompt)

            # Шаг 4: Парсим JSON из ответа
            content = provider.parse_json_response(raw_response)

            # Шаг 5: Валидируем через Pydantic (опционально)
            if self.output_schema and not content.get("parse_error"):
                try:
                    validated = self.output_schema(**content)
                    content = validated.model_dump()
                except ValidationError as e:
                    logger.warning(
                        f"⚠️ [{self.name}] Ошибка валидации Pydantic: {e}. "
                        f"Возвращаем raw content."
                    )

            # Обновляем метку last_used_at
            if self.db_session:
                repo = ChatSessionRepository(self.db_session)
                await repo.touch(self.name)

            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"✅ [{self.name}] завершён за {latency_ms:.0f}ms")

            return {
                "agent_name": self.name,
                "output": content,
                "confidence": self._estimate_confidence(content),
                "latency_ms": round(latency_ms, 2),
                "model_used": "chatgpt-plus-web",
                "prompt_hash": self._prompt_hash,
                "tokens_used": 0,  # Недоступно через веб-интерфейс
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"❌ [{self.name}] ошибка: {e}", exc_info=True)

            return {
                "agent_name": self.name,
                "output": {"error": str(e)},
                "confidence": 0.0,
                "latency_ms": round(latency_ms, 2),
                "model_used": "chatgpt-plus-web",
                "prompt_hash": self._prompt_hash,
                "tokens_used": 0,
            }

    async def _ensure_chat_exists(self, provider: BrowserProvider) -> str:
        """
        Проверить наличие чата в БД.
        Если чата нет — создать новый, отправить системный промпт, сохранить URL.
        Возвращает URL чата.
        """
        # Сначала проверяем кеш в памяти (актуален в рамках одного запуска пайплайна)
        if self._chat_url:
            return self._chat_url

        # Затем проверяем БД
        if self.db_session:
            repo = ChatSessionRepository(self.db_session)
            session_record = await repo.get_session(self.name)

            if session_record and session_record.chat_url:
                logger.info(f"✅ [{self.name}] Чат найден в БД: {session_record.chat_url[:60]}...")
                self._chat_url = session_record.chat_url
                return self._chat_url

        # Чата нет — создаём новый
        logger.info(f"🆕 [{self.name}] Создаём новый чат (системный промпт отправляется 1 раз)...")
        chat_url = await provider.create_chat(self.system_prompt)

        # Сохраняем в БД
        if self.db_session:
            repo = ChatSessionRepository(self.db_session)
            await repo.save_session(self.name, chat_url)

        self._chat_url = chat_url
        logger.info(f"💾 [{self.name}] URL чата сохранён: {chat_url}")
        return chat_url

    def _build_user_prompt(self, context: dict) -> str:
        """
        Сформировать user_prompt из контекста (данные для анализа).
        Переопределяется в дочерних классах.
        По умолчанию — сериализуем весь контекст в компактный JSON.
        """
        return json.dumps(context, ensure_ascii=False, default=str, separators=(",", ":"))

    def _estimate_confidence(self, output: dict) -> float:
        """Оценить уверенность по полноте ответа."""
        if not output or "error" in output or output.get("parse_error"):
            return 0.0
        filled = sum(1 for v in output.values() if v)
        total = max(len(output), 1)
        return round(min(filled / total, 1.0), 2)
