"""
Agentic Investment OS — LLM Provider
Абстракция для работы с LLM через g4f (ChatGPT без API ключа).
"""

import json
import time
from typing import Optional

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    import g4f
    from g4f.client import Client as G4FClient
    G4F_AVAILABLE = True
except ImportError:
    G4F_AVAILABLE = False
    logger.warning("g4f не установлен, LLM недоступен")

from src.config import get_settings

settings = get_settings()


class LLMProvider:
    """
    Абстракция LLM провайдера.
    Использует g4f для доступа к ChatGPT без API ключа.
    """

    def __init__(self, model: str = None, fallback_model: str = None):
        self.model = model or settings.llm_model
        self.fallback_model = fallback_model or settings.llm_fallback_model
        self._client = None

        if G4F_AVAILABLE:
            self._client = G4FClient()
            logger.info(f"🤖 LLM Provider: g4f (model={self.model})")
        else:
            logger.error("❌ g4f недоступен!")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
    )
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        json_mode: bool = True,
    ) -> dict:
        """
        Отправить запрос к LLM и получить структурированный JSON ответ.
        """
        if not self._client:
            raise RuntimeError("LLM Provider не инициализирован")

        start_time = time.time()

        try:
            # Формируем сообщения
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Запрос к g4f
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            raw_content = response.choices[0].message.content
            latency_ms = (time.time() - start_time) * 1000

            # Парсим JSON
            if json_mode:
                parsed = self._extract_json(raw_content)
            else:
                parsed = {"text": raw_content}

            # Оценка количества токенов (приблизительно)
            tokens_estimate = len(system_prompt.split()) + len(user_prompt.split()) + len(raw_content.split())

            logger.debug(
                f"🤖 LLM ответ ({self.model}): "
                f"{latency_ms:.0f}ms, ~{tokens_estimate} tokens"
            )

            return {
                "content": parsed,
                "model": self.model,
                "latency_ms": round(latency_ms, 2),
                "tokens_estimate": tokens_estimate,
                "raw": raw_content,
            }

        except Exception as e:
            logger.warning(f"Ошибка {self.model}, пробуем fallback: {e}")
            # Fallback модель
            return await self._generate_fallback(
                system_prompt, user_prompt, temperature, max_tokens, json_mode
            )

    async def _generate_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> dict:
        """Попытка с fallback моделью."""
        start_time = time.time()

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self._client.chat.completions.create(
                model=self.fallback_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            raw_content = response.choices[0].message.content
            latency_ms = (time.time() - start_time) * 1000

            if json_mode:
                parsed = self._extract_json(raw_content)
            else:
                parsed = {"text": raw_content}

            tokens_estimate = len(system_prompt.split()) + len(user_prompt.split()) + len(raw_content.split())

            logger.info(f"🔄 Fallback LLM ({self.fallback_model}): {latency_ms:.0f}ms")

            return {
                "content": parsed,
                "model": self.fallback_model,
                "latency_ms": round(latency_ms, 2),
                "tokens_estimate": tokens_estimate,
                "raw": raw_content,
            }

        except Exception as e:
            logger.error(f"❌ Fallback тоже не сработал: {e}")
            raise

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Извлечь JSON из ответа LLM (может быть внутри ```json ... ```)."""
        # Пробуем напрямую
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Ищем JSON блок в markdown
        import re
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Ищем любой JSON-подобный объект
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # Если ничего не нашли, оборачиваем в JSON
        logger.warning("⚠️ Не удалось извлечь JSON, возвращаем raw text")
        return {"raw_response": text}
