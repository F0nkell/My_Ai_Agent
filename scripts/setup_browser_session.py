#!/usr/bin/env python3
"""
Agentic Investment OS — Утилита первичной настройки браузерной сессии.

ЗАПУСКАТЬ ОДИН РАЗ на локальной машине с GUI (не на сервере!).
Откроет браузер в видимом режиме, перейдёт на chatgpt.com.
Ты вручную входишь в аккаунт ChatGPT Plus.
После входа нажимаешь Enter — скрипт сохраняет сессию в .browser_data/.

Затем папку .browser_data/ нужно скопировать на ubuntu-сервер.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))


BROWSER_DATA_PATH = ".browser_data"


async def setup_session():
    from playwright.async_api import async_playwright

    print("=" * 60)
    print("🔐 Настройка браузерной сессии ChatGPT Plus")
    print("=" * 60)
    print(f"\nПрофиль браузера будет сохранён в: {BROWSER_DATA_PATH}/")
    print("\nАлгоритм:")
    print("  1. Откроется браузер Chromium")
    print("  2. Перейди на chatgpt.com и залогинься в свой аккаунт Plus")
    print("  3. Убедись, что Google Auth или пароль принят")
    print("  4. Вернись в эту консоль и нажми Enter")
    print("\nПосле этого:")
    print("  • Скопируй папку .browser_data/ на Ubuntu-сервер")
    print("  • Или запусти init_agent_chats.py для создания 5 чатов\n")

    print("Нажми Enter для запуска браузера...")
    input()

    browser_path = Path(BROWSER_DATA_PATH)
    browser_path.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        print("🌐 Запуск Chromium с видимым интерфейсом...")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(browser_path),
            headless=False,  # ВАЖНО: видимый режим для ручного входа
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        page = browser.pages[0] if browser.pages else await browser.new_page()

        print("🔗 Открываем chatgpt.com...")
        await page.goto("https://chatgpt.com/", wait_until="networkidle", timeout=30_000)

        print("\n✅ Браузер открыт!")
        print("=" * 60)
        print("⚡ ШАГ 1: ВХОД В CHATGPT PLUS")
        print("  1. В открывшемся браузере нажми 'Log in'")
        print("  2. Войди через Google или email/пароль")
        print("  3. Дождись главной страницы ChatGPT с полем ввода")
        print("=" * 60)
        print("\nПосле успешного входа в ChatGPT вернись сюда и нажми Enter...")
        input()

        print("🔗 Открываем gemini.google.com...")
        await page.goto("https://gemini.google.com/", wait_until="networkidle", timeout=30_000)

        print("\n=" * 60)
        print("⚡ ШАГ 2: ВХОД В GEMINI ADVANCED")
        print("  1. В браузере (он перешёл на Gemini) нажми 'Войти'")
        print("  2. Войди в свой Google аккаунт (где есть подписка)")
        print("  3. Дождись загрузки нового чата Gemini")
        print("=" * 60)
        print("\nПосле успешного входа в Gemini вернись сюда и нажми Enter...")
        input()

        print("\n💾 Сохраняем сессии (ChatGPT и Gemini) в один профиль браузера...")
        await browser.close()

    print(f"\n✅ Готово! Сессия сохранена в папке: {browser_path.absolute()}/")
    print("\nСледующий шаг:")
    print(f"  1. Скопируй папку на Ubuntu-сервер: scp -r {browser_path}/ user@server:/app/")
    print("  2. Запусти: python scripts/init_agent_chats.py")


if __name__ == "__main__":
    asyncio.run(setup_session())
