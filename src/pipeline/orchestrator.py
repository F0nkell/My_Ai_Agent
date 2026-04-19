"""
Agentic Investment OS — Главный пайплайн оркестрации
Управляет последовательным запуском всех агентов и анализаторов.
"""

import uuid
from datetime import datetime
from typing import Optional

from loguru import logger

from src.database.repositories.analysis import AnalysisRepository
from src.database.repositories.assets import AssetRepository
from src.database.repositories.news import NewsRepository
from src.database.repositories.memory import MemoryRepository
from src.data_layer.market_collector import MarketCollector, MacroCollector
from src.data_layer.preprocessor import DataPreprocessor
from src.signal_engine.engine import SignalEngine
from src.memory.recent import RecentContextManager
from src.memory.thesis import ThesisMemoryManager
from src.agents.chief_planner import ChiefPlannerAgent
from src.agents.news_analyst import NewsAnalystAgent
from src.agents.market_analyst import MarketAnalystAgent
from src.agents.thesis_analyst import ThesisAnalystAgent
from src.agents.chief_investor import ChiefInvestorAgent


class PipelineOrchestrator:
    """Точка входа для запуска полного цикла анализа."""

    def __init__(self, session):
        self.session = session
        self.analysis_repo = AnalysisRepository(session)
        self.asset_repo = AssetRepository(session)
        self.news_repo = NewsRepository(session)
        self.memory_repo = MemoryRepository(session)
        
        self.market_collector = MarketCollector()
        self.macro_collector = MacroCollector()
        self.preprocessor = DataPreprocessor()
        self.signal_engine = SignalEngine()
        
        self.recent_memory = RecentContextManager(self.memory_repo)
        self.thesis_memory = ThesisMemoryManager(self.memory_repo)
        
        self.planner = ChiefPlannerAgent()
        self.news_analyst = NewsAnalystAgent()
        self.market_analyst = MarketAnalystAgent()
        self.thesis_analyst = ThesisAnalystAgent()
        self.investor = ChiefInvestorAgent()

    async def run(self, run_id: uuid.UUID) -> None:
        """Запуск полного пайплайна."""
        logger.info(f"🚀 Запуск пайплайна {run_id}")
        
        try:
            await self.analysis_repo.update_run_status(run_id, "running")
            
            # --- 1. Сбор базовых данных ---
            logger.info("📊 Шаг 1: Сбор базовых данных")
            core_symbols = await self.asset_repo.get_core_symbols()
            watchlist = await self.asset_repo.get_watchlist(active_only=True)
            all_symbols = [item.asset.symbol for item in watchlist]
            
            macro_data = await self.macro_collector.get_macro_data()
            market_data = await self.market_collector.get_market_data(all_symbols)
            unprocessed_news = await self.news_repo.get_unprocessed(limit=100)
            
            # Контекст для планировщика
            planner_context = {
                "current_date": datetime.utcnow().isoformat(),
                "macro_data": macro_data,
                "recent_signals": {}, # Заглушка, в реале брать из БД
                "memory": await self.memory_repo.build_context_for_agent(),
                "last_run_summary": (await self.recent_memory.get_recent_context(1))[0] if await self.recent_memory.get_recent_context(1) else {},
            }
            
            # --- 2. Chief Planner ---
            logger.info("🧠 Шаг 2: Chief Planner генерирует план")
            plan_result = await self.planner.run(planner_context)
            plan = plan_result.get("output", {})
            focus_assets = [a.get("symbol") for a in plan.get("focus_assets", [])]
            
            await self.analysis_repo.set_plan(run_id, plan)
            await self._save_agent_output(run_id, self.planner.name, plan_result)
            
            # --- 3. Фильтрация данных по плану ---
            logger.info("🧹 Шаг 3: Фильтрация данных по плану")
            filtered_news = self.preprocessor.process_news_batch(
                [{"id": n.id, "title": n.title, "content": n.content, "source": n.source, "category": n.category, "asset_symbols": n.asset_symbols, "importance_score": n.importance_score} for n in unprocessed_news],
                plan_filters=plan.get("news_filters", {})
            )
            compact_market_data = self.preprocessor.prepare_market_data_for_agent(
                market_data, focus_symbols=focus_assets if focus_assets else None
            )
            
            # --- 4. Вычисление сигналов ---
            logger.info("📡 Шаг 4: Вычисление сигналов")
            signals_summary = {}
            for item in watchlist:
                symbol = item.asset.symbol
                sector = item.asset.sector
                data = market_data.get(symbol, {})
                news_for_asset = [n for n in filtered_news if symbol in n.get("asset_symbols", [])]
                
                signals = self.signal_engine.compute_all_signals(
                    symbol=symbol,
                    sector=sector,
                    market_data=data,
                    news_items=news_for_asset
                )
                signals_summary[symbol] = signals
            
            # --- 5. News Analyst ---
            logger.info("📰 Шаг 5: News Analyst")
            news_context = {
                "plan_summary": plan.get("summary", ""),
                "focus_assets": focus_assets,
                "news": filtered_news,
            }
            news_result = await self.news_analyst.run(news_context)
            await self._save_agent_output(run_id, self.news_analyst.name, news_result)
            
            # Отмечаем новости как обработанные
            for news in unprocessed_news:
                await self.news_repo.mark_processed(news.id)
            
            # --- 6. Market Analyst ---
            logger.info("📈 Шаг 6: Market Analyst")
            market_context = {
                "market_data": compact_market_data,
                "macro_data": macro_data,
                "signals_summary": signals_summary,
            }
            market_result = await self.market_analyst.run(market_context)
            await self._save_agent_output(run_id, self.market_analyst.name, market_result)
            
            # --- 7. Thesis Analyst ---
            logger.info("🛡️ Шаг 7: Thesis Analyst")
            thesis_context = {
                "thesis_memory": await self.thesis_memory.get_all_theses(),
                "news_analysis": news_result.get("output", {}),
                "market_analysis": market_result.get("output", {}),
                "signals_summary": signals_summary,
                "recent_context": await self.recent_memory.build_context_window(days=7),
            }
            thesis_result = await self.thesis_analyst.run(thesis_context)
            await self._save_agent_output(run_id, self.thesis_analyst.name, thesis_result)
            
            # Обновляем тезисы в памяти
            for update in thesis_result.get("output", {}).get("thesis_updates", []):
                symbol = update.get("symbol")
                status = update.get("thesis_status")
                asset = await self.asset_repo.get_by_symbol(symbol)
                if asset and status:
                    await self.thesis_memory.update_thesis(
                        symbol=symbol,
                        status=status,
                        updates=update,
                        asset_id=asset.id
                    )
            
            # --- 8. Chief Investor ---
            logger.info("🎯 Шаг 8: Chief Investor")
            investor_context = {
                "plan": plan,
                "news_analysis": news_result.get("output", {}),
                "market_analysis": market_result.get("output", {}),
                "thesis_analysis": thesis_result.get("output", {}),
                "signals_summary": signals_summary,
                "memory": await self.memory_repo.build_context_for_agent(),
                "macro_data": macro_data,
            }
            investor_result = await self.investor.run(investor_context)
            await self._save_agent_output(run_id, self.investor.name, investor_result)
            
            # Сохраняем рекомендации
            for rec in investor_result.get("output", {}).get("recommendations", []):
                await self.analysis_repo.save_recommendation(
                    run_id=run_id,
                    asset_symbol=rec.get("symbol"),
                    action=rec.get("action"),
                    reasoning=rec,
                    confidence=rec.get("confidence", 0.5),
                    priority=rec.get("priority", 5),
                    target_price=rec.get("target_price"),
                    stop_loss=rec.get("stop_loss"),
                )
            
            # Обновляем недавний контекст
            await self.recent_memory.save_run_summary({
                "run_id": str(run_id),
                "market_assessment": investor_result.get("output", {}).get("market_assessment", ""),
                "recommendations_count": len(investor_result.get("output", {}).get("recommendations", [])),
                "summary": investor_result.get("output", {}).get("summary", ""),
            })
            
            # --- 9. Завершение ---
            logger.info("✅ Пайплайн успешно завершён")
            await self.analysis_repo.update_run_status(run_id, "completed")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в пайплайне: {e}", exc_info=True)
            await self.analysis_repo.update_run_status(run_id, "failed", error_message=str(e))

    async def _save_agent_output(self, run_id: uuid.UUID, agent_name: str, result: dict) -> None:
        """Вспомогательный метод для сохранения выхода агента."""
        await self.analysis_repo.save_agent_output(
            run_id=run_id,
            agent_name=agent_name,
            output=result.get("output", {}),
            confidence=result.get("confidence", 0.0),
            tokens_used=result.get("tokens_used", 0),
            latency_ms=result.get("latency_ms", 0.0),
            model_used=result.get("model_used"),
            prompt_hash=result.get("prompt_hash")
        )
