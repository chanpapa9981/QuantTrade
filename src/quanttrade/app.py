from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from quanttrade.audit.logger import configure_logging
from quanttrade.backtest.engine import BacktestEngine
from quanttrade.backtest.exporter import export_backtest_result
from quanttrade.config.loader import load_settings
from quanttrade.core.types import AccountState, MarketBar, PositionState
from quanttrade.dashboard.service import build_dashboard_payload, build_history_payload
from quanttrade.dashboard.html import render_dashboard_html, render_history_html
from quanttrade.data.importer import import_bars_from_csv
from quanttrade.data.repository import BacktestRunRepository, BarRepository
from quanttrade.data.schema import create_schema
from quanttrade.data.storage import database_lock, ensure_data_dirs
from quanttrade.execution.simulator import SimulatedExecutionEngine
from quanttrade.risk.engine import RiskEngine
from quanttrade.strategies.atr_dtf import AtrDynamicTrendFollowingStrategy


class QuantTradeApp:
    def __init__(self, config_path: str) -> None:
        self.settings = load_settings(config_path)
        configure_logging()
        ensure_data_dirs(self.settings.data.duckdb_path)

    def doctor(self) -> dict[str, object]:
        return {
            "app": asdict(self.settings.app),
            "strategy": asdict(self.settings.strategy),
            "risk": asdict(self.settings.risk),
            "data_path": self.settings.data.duckdb_path,
            "data_backend": self.settings.data.backend,
            "execution": asdict(self.settings.execution),
        }

    def run_sample(self) -> dict[str, object]:
        strategy = AtrDynamicTrendFollowingStrategy(self.settings.strategy)
        risk_engine = RiskEngine(self.settings.risk)
        execution_engine = SimulatedExecutionEngine(self.settings.execution)
        engine = BacktestEngine(strategy, risk_engine, execution_engine)

        market_bar = MarketBar(
            timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=104.0,
            low=99.0,
            close=105.0,
            volume=2_000_000,
            atr=2.0,
            adx=30.0,
            donchian_high=103.0,
            donchian_low=96.0,
        )
        account_state = AccountState(equity=100_000.0, cash=100_000.0)
        position_state = PositionState(symbol=self.settings.strategy.symbol)
        result = engine.run_once(market_bar, account_state, position_state)
        return asdict(result)

    def import_csv(self, csv_path: str, symbol: str, timeframe: str = "1d") -> dict[str, object]:
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            inserted = import_bars_from_csv(
                csv_path=csv_path,
                db_path=self.settings.data.duckdb_path,
                symbol=symbol,
                timeframe=timeframe,
            )
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "rows_inserted": inserted,
            "data_path": self.settings.data.duckdb_path,
        }

    def backtest_symbol(self, symbol: str, timeframe: str = "1d", initial_equity: float = 100_000.0) -> dict[str, object]:
        with database_lock(self.settings.data.duckdb_path):
            repository = BarRepository(self.settings.data.duckdb_path)
            bars = repository.fetch_bars(symbol=symbol, timeframe=timeframe)
        strategy_config = self.settings.strategy
        strategy_config.symbol = symbol
        strategy = AtrDynamicTrendFollowingStrategy(strategy_config)
        risk_engine = RiskEngine(self.settings.risk)
        execution_engine = SimulatedExecutionEngine(self.settings.execution)
        engine = BacktestEngine(strategy, risk_engine, execution_engine)
        result = engine.run_series(bars=bars, initial_equity=initial_equity)
        return asdict(result)

    def persist_backtest_run(
        self,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
    ) -> dict[str, object]:
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BarRepository(self.settings.data.duckdb_path)
            bars = repository.fetch_bars(symbol=symbol, timeframe=timeframe)
            strategy_config = self.settings.strategy
            strategy_config.symbol = symbol
            strategy = AtrDynamicTrendFollowingStrategy(strategy_config)
            risk_engine = RiskEngine(self.settings.risk)
            execution_engine = SimulatedExecutionEngine(self.settings.execution)
            engine = BacktestEngine(strategy, risk_engine, execution_engine)
            payload = asdict(engine.run_series(bars=bars, initial_equity=initial_equity))
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            run_id = repository.save_run(symbol=symbol, timeframe=timeframe, payload=payload)
        return {
            "run_id": run_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "bars_processed": payload["bars_processed"],
            "metrics": payload["metrics"],
        }

    def recent_backtest_runs(self, limit: int = 10) -> dict[str, object]:
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"runs": repository.fetch_recent_runs(limit=limit)}

    def backtest_run_detail(self, run_id: str) -> dict[str, object]:
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            detail = repository.fetch_run_detail(run_id)
            return {"detail": detail}

    def recent_order_events(self, limit: int = 20) -> dict[str, object]:
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"orders": repository.fetch_recent_order_events(limit=limit)}

    def recent_audit_events(self, limit: int = 20) -> dict[str, object]:
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"audit_events": repository.fetch_recent_audit_events(limit=limit)}

    def dashboard_history(self, runs_limit: int = 20, events_limit: int = 20) -> dict[str, object]:
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            bundle = repository.fetch_history_bundle(runs_limit=runs_limit, events_limit=events_limit)
            return build_history_payload(bundle["runs"], bundle["orders"], bundle["audit_events"])

    def export_backtest(
        self,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
        output_path: str = "var/reports/backtest.json",
    ) -> dict[str, object]:
        payload = self.backtest_symbol(symbol=symbol, timeframe=timeframe, initial_equity=initial_equity)
        written_path = export_backtest_result(payload, output_path)
        return {
            "output_path": written_path,
            "symbol": symbol,
            "bars_processed": payload["bars_processed"],
            "metrics": payload["metrics"],
        }

    def dashboard_snapshot(
        self,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
    ) -> dict[str, object]:
        backtest_payload = self.backtest_symbol(symbol=symbol, timeframe=timeframe, initial_equity=initial_equity)
        return build_dashboard_payload(backtest_payload)

    def export_dashboard_snapshot(
        self,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
        output_path: str = "var/reports/dashboard.json",
    ) -> dict[str, object]:
        payload = self.dashboard_snapshot(symbol=symbol, timeframe=timeframe, initial_equity=initial_equity)
        written_path = export_backtest_result(payload, output_path)
        return {
            "output_path": written_path,
            "symbol": symbol,
            "summary_cards": len(payload["summary_cards"]),
            "recent_trades": len(payload["recent_trades"]),
        }

    def export_dashboard_html(
        self,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
        output_path: str = "var/reports/dashboard.html",
    ) -> dict[str, object]:
        payload = self.dashboard_snapshot(symbol=symbol, timeframe=timeframe, initial_equity=initial_equity)
        written_path = render_dashboard_html(payload, output_path)
        return {
            "output_path": written_path,
            "symbol": symbol,
            "summary_cards": len(payload["summary_cards"]),
            "recent_trades": len(payload["recent_trades"]),
        }

    def export_history_html(
        self,
        runs_limit: int = 20,
        events_limit: int = 20,
        output_path: str = "var/reports/history.html",
    ) -> dict[str, object]:
        payload = self.dashboard_history(runs_limit=runs_limit, events_limit=events_limit)
        written_path = render_history_html(payload, output_path)
        return {
            "output_path": written_path,
            "runs": len(payload["runs_table"]),
            "orders": len(payload["recent_orders"]),
            "audit_events": len(payload["recent_audit_events"]),
        }
