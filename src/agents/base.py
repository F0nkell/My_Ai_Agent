"""
Agentic Investment OS — Базовый агент
Общая логика для всех агентов: валидация, логирование, вызов LLM.
"""

import hashlib
import time
from typing import Optional, Type

from loguru import logger
from pydantic import BaseModel, ValidationError

from src.agents.llm_provider import LLMProvider


class BaseAgent:
    """
    Базовый класс для всех агентов.
    Обеспечивает:
    - Загрузку промпта из файла
    - Вызов LLM
    - Валидацию JSON через Pydantic
    - Логирование
    """

    name: str = "base_agent"
    prompt_template: str = ""
    output_schema: Optional[Type[BaseModel]] = None

    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or LLMProvider()
        self._prompt_hash = ""

    async def run(self, context: dict) -> dict:
        """
        Главный метод — запуск агента.
        1. Формирование промпта
        2. Вызов LLM
        3. Валидация JSON
        4. Возврат результата
        """
        start_time = time.time()
        logger.info(f"🤖 Агент [{self.name}] запускается...")

        try:
            # 1. Формируем промпт
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_user_prompt(context)

            # Хеш промпта для версионирования
            self._prompt_hash = hashlib.sha256(
                system_prompt.encode()
            ).hexdigest()[:16]

            # 2. Вызов LLM
            llm_result = await self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=True,
            )

            content = llm_result["content"]

            # 3. Валидация через Pydantic
            if self.output_schema:
                try:
                    validated = self.output_schema(**content)
                    content = validated.model_dump()
                except ValidationError as e:
                    logger.warning(
                        f"⚠️ [{self.name}] Ошибка валидации: {e}. "
                        f"Возвращаем raw content."
                    )

            latency_ms = (time.time() - start_time) * 1000

            result = {
                "agent_name": self.name,
                "output": content,
                "confidence": self._estimate_confidence(content),
                "tokens_used": llm_result.get("tokens_estimate", 0),
                "latency_ms": round(latency_ms, 2),
                "model_used": llm_result.get("model", "unknown"),
                "prompt_hash": self._prompt_hash,
            }

            logger.info(
                f"✅ [{self.name}] завершён: "
                f"{latency_ms:.0f}ms, ~{result['tokens_used']} tokens"
            )

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"❌ [{self.name}] ошибка: {e}")

            return {
                "agent_name": self.name,
                "output": {"error": str(e)},
                "confidence": 0.0,
                "tokens_used": 0,
                "latency_ms": round(latency_ms, 2),
                "model_used": "error",
                "prompt_hash": self._prompt_hash,
            }

    def _get_system_prompt(self) -> str:
        """Получить системный промпт агента."""
        return self.prompt_template

    def _build_user_prompt(self, context: dict) -> str:
        """Сформировать пользовательский промпт из контекста."""
        # Минимизируем токены — передаём только нужные данные
        import json
        return json.dumps(context, ensure_ascii=False, default=str)

    def _estimate_confidence(self, output: dict) -> float:
        """Оценить уверенность по полноте ответа."""
        if not output or "error" in output:
            return 0.0

        # Считаем заполненные поля
        filled = sum(1 for v in output.values() if v)
        total = max(len(output), 1)
        return round(min(filled / total, 1.0), 2)
