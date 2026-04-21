"""
Agentic Investment OS — Browser Provider (Playwright)
Взаимодействие с ChatGPT через веб-интерфейс (подписка Plus).
Использует Playwright для управления браузером с постоянной сессией.

Архитектура:
- Persistent Context — браузер сохраняет куки/сессию между запусками.
- 5 независимых чатов (по одному на каждого агента).
- Stateful: системный промпт отправляется ОДИН раз при создании чата.
- Последующие вызовы только отправляют данные (user prompt).
"""

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Optional

from loguru import logger


# CSS-селекторы ChatGPT (актуальные для веб-интерфейса)
# Если OpenAI обновит интерфейс — обновить здесь
SELECTORS = {
    "prompt_textarea": "#prompt-textarea",
    "send_button": 'button[data-testid="send-button"]',
    "new_chat_button": 'a[href="/"]',  # Кнопка "New chat"
    "stop_button": 'button[data-testid="stop-button"]',  # Кнопка стоп во время генерации
    # Последнее сообщение ассистента
    "last_response": '[data-testid^="conversation-turn-"]:last-child .markdown',
    # Индикатор загрузки (когда GPT печатает)
    "streaming_indicator": 'button[data-testid="stop-button"]',
}

CHATGPT_URL = "https://chatgpt.com/"
GENERATION_TIMEOUT_SEC = 300  # 5 минут максимум на генерацию ответа
GENERATION_POLL_INTERVAL_SEC = 2  # Каждые 2 секунды проверяем — закончил ли печатать
PAGE_LOAD_TIMEOUT_MS = 30_000


class BrowserProvider:
    """
    Провайдер LLM на базе Playwright.
    Управляет браузером с постоянным профилем (persistent context),
    создаёт чаты и отправляет в них сообщения.
    """

    def __init__(self, browser_data_path: str = ".browser_data"):
        self.browser_data_path = Path(browser_data_path)
        self.browser_data_path.mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._browser = None
        self._page = None

    async def init(self) -> None:
        """
        Запуск Playwright с постоянным профилем браузера.
        Профиль сохраняется в `browser_data_path`, поэтому достаточно
        один раз залогиниться вручную через `scripts/setup_browser_session.py`.
        """
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        logger.info(f"🌐 Запуск Chromium (persistent profile: {self.browser_data_path})")
        self._browser = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.browser_data_path),
            headless=True,  # True для сервера (headless). False для первого входа.
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",  # Скрыть следы автоматизации
            ],
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        # Открываем или переиспользуем первую страницу
        pages = self._browser.pages
        if pages:
            self._page = pages[0]
        else:
            self._page = await self._browser.new_page()

        logger.info("✅ Браузер инициализирован")

    async def close(self) -> None:
        """Закрыть браузер и завершить Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("🔴 Браузер закрыт")

    async def create_chat(self, system_prompt: str) -> str:
        """
        Создать новый чат на ChatGPT и отправить системный промпт первым сообщением.

        Returns:
            str: URL созданного чата (например https://chatgpt.com/c/<uuid>)
        """
        if not self._page:
            raise RuntimeError("Browser не инициализирован. Вызовите init() сначала.")

        logger.info("🆕 Создание нового чата...")

        # Переходим на главную — это создаёт новый чат
        await self._page.goto(CHATGPT_URL, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
        await asyncio.sleep(2)

        # Отправляем системный промпт как первое сообщение
        logger.info("📤 Отправляем системный промпт в новый чат...")
        await self._send_message_to_page(system_prompt)

        # Ждём завершения ответа GPT на системный промпт
        await self._wait_for_generation_complete()

        # Читаем URL — он изменится с "/" на "/c/<uuid>" после первого сообщения
        chat_url = self._page.url
        logger.info(f"✅ Чат создан: {chat_url}")

        return chat_url

    async def send_message(self, chat_url: str, message: str) -> str:
        """
        Перейти к существующему чату и отправить сообщение.

        Args:
            chat_url: URL чата (из БД)
            message: Текст сообщения (user prompt с данными для анализа)

        Returns:
            str: Текстовый ответ ChatGPT
        """
        if not self._page:
            raise RuntimeError("Browser не инициализирован.")

        logger.info(f"💬 Отправка сообщения в чат: {chat_url[:60]}...")

        # Открываем нужный чат
        current_url = self._page.url
        if current_url.rstrip("/") != chat_url.rstrip("/"):
            await self._page.goto(chat_url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
            await asyncio.sleep(2)

        # Отправляем сообщение
        await self._send_message_to_page(message)

        # Ждём ответа
        await self._wait_for_generation_complete()

        # Извлекаем последний ответ
        response_text = await self._get_last_response()
        logger.info(f"📥 Получен ответ ({len(response_text)} символов)")

        return response_text

    async def _send_message_to_page(self, text: str) -> None:
        """
        Внутренний метод: вписать текст в поле промпта и нажать отправить.
        Обходит ограничения React-контролируемых textarea через clipboard.
        """
        # Находим textarea
        textarea = await self._page.wait_for_selector(
            SELECTORS["prompt_textarea"],
            timeout=PAGE_LOAD_TIMEOUT_MS,
        )

        # Вставляем текст через clipboard (надёжнее чем type() для длинных текстов)
        await self._page.evaluate(
            """(text) => {
                const dt = new DataTransfer();
                dt.setData('text/plain', text);
                const el = document.querySelector('#prompt-textarea');
                el.focus();
                document.execCommand('insertText', false, text);
            }""",
            text,
        )

        await asyncio.sleep(0.5)

        # Нажимаем кнопку отправки
        send_btn = await self._page.wait_for_selector(
            SELECTORS["send_button"],
            state="visible",
            timeout=10_000,
        )
        await send_btn.click()
        logger.debug("✉️ Сообщение отправлено, ожидаем ответ...")

    async def _wait_for_generation_complete(self) -> None:
        """
        Ждать, пока ChatGPT не закончит печатать ответ.
        Стратегия: ждём появления кнопки Stop → затем её исчезновения.
        """
        start_time = time.time()

        # Ждём появления индикатора стриминга (кнопка Stop)
        try:
            await self._page.wait_for_selector(
                SELECTORS["streaming_indicator"],
                state="visible",
                timeout=15_000,  # 15 секунд на появление ответа
            )
        except Exception:
            logger.warning("⚠️ Кнопка Stop не появилась — возможно ответ мгновенный")
            await asyncio.sleep(2)
            return

        # Ждём исчезновения кнопки Stop — это означает конец генерации
        try:
            await self._page.wait_for_selector(
                SELECTORS["streaming_indicator"],
                state="hidden",
                timeout=GENERATION_TIMEOUT_SEC * 1000,
            )
        except Exception:
            elapsed = time.time() - start_time
            logger.error(f"❌ Таймаут генерации после {elapsed:.0f}с")
            raise TimeoutError("ChatGPT не завершил генерацию в отведённое время")

        # Дополнительная пауза для полного рендера DOM
        await asyncio.sleep(1.5)
        elapsed = time.time() - start_time
        logger.debug(f"⏱️ Генерация завершена за {elapsed:.1f}с")

    async def _get_last_response(self) -> str:
        """
        Извлечь текст последнего ответа ассистента со страницы.
        """
        try:
            # Берём все элементы ответа ассистента
            responses = await self._page.query_selector_all(SELECTORS["last_response"])
            if not responses:
                raise ValueError("Ответ не найден на странице")

            # Берём последний
            last = responses[-1]
            text = await last.inner_text()
            return text.strip()

        except Exception as e:
            logger.error(f"❌ Не удалось извлечь ответ: {e}")
            # Фоллбэк: вернуть весь текст страницы
            return await self._page.inner_text("body")

    def parse_json_response(self, raw_text: str) -> dict:
        """
        Извлечь JSON из ответа ChatGPT.
        Агент должен отвечать строго в JSON, но GPT иногда добавляет обёртку.
        """
        # Попытка 1: прямой парсинг
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass

        # Попытка 2: JSON внутри ```json ... ```
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Попытка 3: первый JSON-объект в тексте
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error("❌ Не удалось распарсить JSON из ответа GPT")
        logger.debug(f"RAW ответ: {raw_text[:500]}")
        return {"raw_response": raw_text, "parse_error": True}


# Глобальный синглтон провайдера (один экземпляр на процесс)
_provider_instance: Optional[BrowserProvider] = None


async def get_browser_provider(browser_data_path: str = ".browser_data") -> BrowserProvider:
    """Получить инициализированный синглтон BrowserProvider."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = BrowserProvider(browser_data_path=browser_data_path)
        await _provider_instance.init()
    return _provider_instance


async def shutdown_browser_provider() -> None:
    """Закрыть браузер при завершении приложения."""
    global _provider_instance
    if _provider_instance is not None:
        await _provider_instance.close()
        _provider_instance = None
