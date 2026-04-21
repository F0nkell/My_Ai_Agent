"""
Agentic Investment OS — Gemini Provider (Playwright)
Прокси для пересылки сообщений в веб-интерфейс Gemini (чат Smeam).
Использует ту же браузерную сессию, что и ChatGPT.
"""

import asyncio
import time
from typing import Optional

from loguru import logger

from src.config import get_settings

# CSS-селекторы Gemini (динамично меняются, берём надёжные aria/role)
SELECTORS = {
    # Поле ввода текста (обычно это contenteditable div)
    "prompt_input": 'div[contenteditable="true"][role="textbox"]',
    # Кнопка отправки (может иметь aria-label "Send message")
    "send_button": 'button[aria-label*="Send message"], button[aria-label*="Отправить сообщение"]',
    # Окончательный ответ ассистента
    "response_container": 'message-content',
    # Индикатор генерации (кнопка остановки)
    "stop_button": 'button[aria-label*="Stop generating"], button[aria-label*="Остановить"]'
}

PAGE_LOAD_TIMEOUT_MS = 40_000


class GeminiProvider:
    """Управление веб-интерфейсом Gemini через существующий Playwright browser."""

    def __init__(self, browser):
        self._browser = browser
        self._page = None
        self._settings = get_settings()

    async def get_page(self):
        """Возвращает существующую вкладку Gemini или открывает новую."""
        if not self._page:
            self._page = await self._browser.new_page()
            logger.info(f"🔗 Открываем чат Gemini: {self._settings.gemini_chat_url}")
            await self._page.goto(self._settings.gemini_chat_url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
            await asyncio.sleep(3)
        return self._page

    async def send_message(self, message: str) -> str:
        """Отправить сообщение стратегу в Gemini и получить ответ."""
        page = await self.get_page()

        # Убеждаемся, что мы в нужном чате
        current_url = page.url
        if current_url.rstrip("/") != self._settings.gemini_chat_url.rstrip("/"):
            await page.goto(self._settings.gemini_chat_url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
            await asyncio.sleep(2)

        logger.info("💬 Отправка сообщения в Gemini Smeam...")

        # Ввод текста (Gemini использует rich-textarea)
        input_box = await page.wait_for_selector(SELECTORS["prompt_input"], timeout=10_000)
        await input_box.focus()

        # Очищаем поле (если вдруг что-то было)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")

        # Для длинных текстов в contenteditable лучше вставлять через clipboard или type
        await page.evaluate(
            """(text) => {
                const dt = new DataTransfer();
                dt.setData('text/plain', text);
                const el = document.querySelector('div[contenteditable="true"][role="textbox"]');
                el.focus();
                document.execCommand('insertText', false, text);
            }""",
            message,
        )
        await asyncio.sleep(0.5)

        # Жмём кнопку отправить
        try:
            send_btn = await page.query_selector(SELECTORS["send_button"])
            if send_btn:
                await send_btn.click()
            else:
                # Если кнопки нет - жмём Enter
                await page.keyboard.press("Enter")
        except Exception as e:
            logger.warning(f"Кнопка отправки не найдена, жмем Enter: {e}")
            await page.keyboard.press("Enter")

        logger.debug("✉️ Сообщение в Gemini отправлено, ожидаем генерацию...")
        return await self._wait_and_extract_response(page)

    async def _wait_and_extract_response(self, page) -> str:
        """Ждёт окончания генерации и парсит ответ."""
        start_time = time.time()

        # В Gemini может появиться кнопка Stop Generating, ждем её исчезновения
        # Либо ждём когда кнопка Send снова станет доступной (она пропадает или блокируется)
        try:
            # Даем Gemini 5 секунд начать думать
            await asyncio.sleep(5)
            
            # Ждем пока кнопка Send снова станет активной (признак окончания генерации)
            # Либо просто ждём когда DOM перестанет быстро меняться
            for _ in range(30):
                await asyncio.sleep(2)
                # Пробуем найти спиннер или кнопку Stop (если есть - продолжаем ждать)
                stop_btn = await page.query_selector(SELECTORS["stop_button"])
                if not stop_btn:
                    # Проверим, доступна ли кнопка Send
                    send = await page.query_selector(SELECTORS["send_button"])
                    if send and await send.is_enabled():
                        break
        except Exception as e:
            logger.error(f"Ошибка ожидания Gemini: {e}")

        # Дополнительная пауза для финального рендера
        await asyncio.sleep(2)
        elapsed = time.time() - start_time
        logger.debug(f"⏱️ Генерация Gemini завершена за {elapsed:.1f}с")

        # Извлекаем последний ответ
        try:
            responses = await page.query_selector_all(SELECTORS["response_container"])
            if not responses:
                raise ValueError("Ответ Gemini не найден на странице")
            last = responses[-1]
            text = await last.inner_text()
            return text.strip()
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения Gemini ответа: {e}")
            return "К сожалению, не удалось прочитать ответ от Gemini (изменилась верстка страницы)."
