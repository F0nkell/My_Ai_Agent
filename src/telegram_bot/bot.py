"""
Agentic Investment OS — Telegram Bot Setup
Инициализация бота и привязка хендлеров.
"""

from loguru import logger
from telegram.ext import Application, CommandHandler

from src.config import get_settings
from src.telegram_bot.handlers import (
    start_command,
    portfolio_command,
    run_command,
    latest_command
)

settings = get_settings()

def get_telegram_app() -> Application:
    """Создает и настраивает приложение Telegram бота."""
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN не установлен. Бот не будет работать.")
        return None

    try:
        app = Application.builder().token(settings.telegram_bot_token).build()

        # Регистрируем обработчики команд
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("portfolio", portfolio_command))
        app.add_handler(CommandHandler("run", run_command))
        app.add_handler(CommandHandler("latest", latest_command))

        logger.info("📱 Telegram Бот инициализирован")
        return app
    except Exception as e:
        logger.error(f"Ошибка инициализации Telegram бота: {e}")
        return None

# Функция для запуска бота (будет вызвана в main.py или отдельным скриптом)
def run_bot():
    app = get_telegram_app()
    if app:
        logger.info("Запуск Telegram бота (polling)...")
        app.run_polling()
