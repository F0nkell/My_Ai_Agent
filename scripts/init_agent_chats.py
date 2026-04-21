#!/usr/bin/env python3
"""
Agentic Investment OS — Инициализация 5 чатов агентов.

Запустить ПОСЛЕ setup_browser_session.py (когда сессия уже сохранена).
Скрипт:
1. Открывает браузер с сохранённым профилем.
2. Создаёт 5 чатов на chatgpt.com (по одному на каждого агента).
3. Отправляет в каждый чат системный промпт агента.
4. Сохраняет URL чатов в базу данных (web_chat_sessions).

Запуск:
    python scripts/init_agent_chats.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def init_chats():
    """Инициализировать все 5 чатов агентов."""
    from src.config import get_settings
    from src.database import get_async_session
    from src.agents.browser_provider import BrowserProvider
    from src.agents.chief_planner import ChiefPlannerAgent
    from src.agents.news_analyst import NewsAnalystAgent
    from src.agents.market_analyst import MarketAnalystAgent
    from src.agents.thesis_analyst import ThesisAnalystAgent
    from src.agents.chief_investor import ChiefInvestorAgent
    from src.database.repositories.chat_sessions import ChatSessionRepository

    settings = get_settings()

    print("=" * 60)
    print("🤖 Инициализация чатов агентов на ChatGPT Plus")
    print("=" * 60)
    print(f"Профиль браузера: {settings.browser_data_path}")
    print("")

    # Список агентов с их системными промптами
    agents = [
        ("chief_planner",   ChiefPlannerAgent.system_prompt),
        ("news_analyst",    NewsAnalystAgent.system_prompt),
        ("market_analyst",  MarketAnalystAgent.system_prompt),
        ("thesis_analyst",  ThesisAnalystAgent.system_prompt),
        ("chief_investor",  ChiefInvestorAgent.system_prompt),
    ]

    # Инициализируем браузер
    provider = BrowserProvider(browser_data_path=settings.browser_data_path)
    await provider.init()

    try:
        async with get_async_session() as session:
            repo = ChatSessionRepository(session)

            for agent_name, system_prompt in agents:
                # Проверяем — может чат уже есть
                existing = await repo.get_session(agent_name)
                if existing:
                    print(f"⏭️  [{agent_name}] Чат уже существует: {existing.chat_url[:60]}...")
                    print(f"   Хочешь пересоздать? (y/N): ", end="")
                    choice = input().strip().lower()
                    if choice != "y":
                        continue
                    else:
                        await repo.delete_session(agent_name)

                print(f"\n🆕 [{agent_name}] Создаём чат...")
                print(f"   Отправляем системный промпт ({len(system_prompt)} символов)...")

                chat_url = await provider.create_chat(system_prompt)
                await repo.save_session(agent_name, chat_url)

                print(f"   ✅ URL: {chat_url}")
                print(f"   ⏳ Пауза 3 секунды перед следующим чатом...")
                await asyncio.sleep(3)

        print("\n" + "=" * 60)
        print("✅ Все чаты инициализированы!")
        print("=" * 60)
        print("\nСводка чатов:")

        async with get_async_session() as session:
            repo = ChatSessionRepository(session)
            all_sessions = await repo.get_all_sessions()
            for s in all_sessions:
                print(f"  [{s.agent_name:20s}] {s.chat_url}")

    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(init_chats())
