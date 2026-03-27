from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from quanttrade.audit.logger import configure_logging
from quanttrade.backtest.engine import BacktestEngine
from quanttrade.backtest.exporter import export_backtest_result
from quanttrade.config.loader import load_settings
from quanttrade.core.types import AccountState, MarketBar, PositionState
from quanttrade.data.importer import import_bars_from_csv
from quanttrade.data.repository import BarRepository
from quanttrade.data.storage import ensure_data_dirs
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
        }

    def run_sample(self) -> dict[str, object]:
        strategy = AtrDynamicTrendFollowingStrategy(self.settings.strategy)
        risk_engine = RiskEngine(self.settings.risk)
        engine = BacktestEngine(strategy, risk_engine)

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
        repository = BarRepository(self.settings.data.duckdb_path)
        bars = repository.fetch_bars(symbol=symbol, timeframe=timeframe)
        strategy_config = self.settings.strategy
        strategy_config.symbol = symbol
        strategy = AtrDynamicTrendFollowingStrategy(strategy_config)
        risk_engine = RiskEngine(self.settings.risk)
        engine = BacktestEngine(strategy, risk_engine)
        result = engine.run_series(bars=bars, initial_equity=initial_equity)
        return asdict(result)

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
