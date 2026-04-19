"""
Agentic Investment OS — Telegram Bot Handlers
"""

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from src.config import get_settings
from src.database import async_session_factory
from src.database.repositories.analysis import AnalysisRepository
from src.pipeline.tasks import run_pipeline_task
from src.telegram_bot.formatters import format_recommendations, format_portfolio_status

settings = get_settings()

async def check_auth(update: Update) -> bool:
    """Проверка ID пользователя (отвечаем только владельцу)."""
    if str(update.effective_chat.id) != settings.telegram_chat_id:
        logger.warning(f"Неавторизованный доступ от {update.effective_chat.id}")
        await update.message.reply_text("⛔ Доступ запрещен. Вы не являетесь владельцем.")
        return False
    return True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    if not await check_auth(update): return
    
    welcome_text = (
        "👋 Привет! Я — *Agentic Investment OS*.\n"
        "Ваш персональный ИИ-директор по инвестициям.\n\n"
        "Моя задача — вести вас к цели (пассивный доход $10к) через стратегию _«Русский Спринт 2026-2032»_.\n\n"
        "Доступные команды:\n"
        "/portfolio — Текущий статус портфеля\n"
        "/run — Запустить полный цикл анализа СЕЙЧАС\n"
        "/latest — Последние инсайты и рекомендации\n"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать текущий портфель."""
    if not await check_auth(update): return
    
    # В реальном приложении это бралось бы из БД или API брокера,
    # здесь берём из нашего config.py (settings.default_watchlist)
    from src.api.routes import get_portfolio
    import asyncio
    
    # Так как get_portfolio это async роут, вызываем его
    portfolio = await get_portfolio()
    
    text = format_portfolio_status(portfolio)
    await update.message.reply_text(text, parse_mode="Markdown")

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ручной запуск пайплайна."""
    if not await check_auth(update): return
    
    await update.message.reply_text("🚀 Запускаю полный цикл анализа... Это займет 1-3 минуты. Я сообщу о результатах.")
    
    # Создаем прогон в БД
    async with async_session_factory() as session:
        repo = AnalysisRepository(session)
        run = await repo.create_run(trigger="manual_telegram")
        run_id = str(run.id)
    
    # Отправляем в Celery
    run_pipeline_task.delay(run_id)
    
async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получить последние рекомендации."""
    if not await check_auth(update): return
    
    async with async_session_factory() as session:
        repo = AnalysisRepository(session)
        runs = await repo.get_recent_runs(limit=1)
        
        if not runs or runs[0].status != "completed":
            await update.message.reply_text("Пока нет завершенных прогонов анализа. Запустите /run")
            return
            
        latest_run = runs[0]
        recs = await repo.get_latest_recommendations(limit=20)
        
        # Фильтруем только для последнего прогона
        run_recs = [r for r in recs if r.run_id == latest_run.id]
        
        # Извлекаем summary прогона из agent_outputs (у Chief Investor)
        investor_output = next((o for o in latest_run.agent_outputs if o.agent_name == "chief_investor"), None)
        summary_data = investor_output.output if investor_output else {}
        
        # Конвертируем ORM объекты рекомендаций в dict для форматера
        recs_dicts = [
            {
                "symbol": r.asset_symbol,
                "action": r.action,
                "confidence": r.confidence,
                "priority": r.priority,
                "target_price": r.target_price,
                "stop_loss": r.stop_loss,
                "reasoning": r.reasoning.get("reasoning", r.reasoning) if isinstance(r.reasoning, dict) else r.reasoning
            } for r in run_recs
        ]
        
        text = format_recommendations(summary_data, recs_dicts)
        await update.message.reply_text(text, parse_mode="Markdown")
