from __future__ import annotations

from dataclasses import asdict, dataclass

from quanttrade.core.types import (
    AccountState,
    BacktestMetrics,
    BacktestRunResult,
    MarketBar,
    PositionState,
    SignalType,
)
from quanttrade.data.indicators import enrich_market_bars
from quanttrade.execution.simulator import SimulatedExecutionEngine
from quanttrade.risk.engine import RiskEngine
from quanttrade.strategies.base import Strategy


@dataclass(slots=True)
class BacktestStepResult:
    signal: str
    reason: str
    risk_allowed: bool
    execution_reason: str
    position_quantity: int


class BacktestEngine:
    def __init__(self, strategy: Strategy, risk_engine: RiskEngine) -> None:
        self.strategy = strategy
        self.risk_engine = risk_engine
        self.execution_engine = SimulatedExecutionEngine()

    def run_once(
        self,
        market_bar: MarketBar,
        account_state: AccountState,
        position_state: PositionState,
    ) -> BacktestStepResult:
        decision = self.strategy.generate_signal(market_bar, position_state, account_state)
        risk_result = self.risk_engine.validate(account_state, decision)

        if not risk_result.allowed and decision.signal != SignalType.LONG_EXIT:
            return BacktestStepResult(
                signal=decision.signal.value,
                reason=decision.reason,
                risk_allowed=False,
                execution_reason=risk_result.reason,
                position_quantity=position_state.quantity,
            )

        execution = self.execution_engine.execute(
            timestamp=market_bar.timestamp,
            symbol=position_state.symbol or self.strategy.config.symbol,
            market_price=market_bar.close,
            account_state=account_state,
            position_state=position_state,
            decision=decision,
        )
        return BacktestStepResult(
            signal=decision.signal.value,
            reason=decision.reason,
            risk_allowed=risk_result.allowed,
            execution_reason=execution.reason,
            position_quantity=execution.position_state.quantity,
        )

    def run_series(
        self,
        bars: list[MarketBar],
        initial_equity: float,
    ) -> BacktestRunResult:
        symbol = self.strategy.config.symbol
        account_state = AccountState(equity=initial_equity, cash=initial_equity)
        position_state = PositionState(symbol=symbol)
        trades: list[dict[str, str | float | int]] = []
        equity_curve: list[float] = [initial_equity]
        winning_trades = 0

        enriched_bars = enrich_market_bars(
            bars=bars,
            atr_period=self.strategy.config.atr_smooth_period,
            adx_period=self.strategy.config.atr_smooth_period,
            entry_donchian_n=self.strategy.config.entry_donchian_n,
            exit_donchian_m=self.strategy.config.exit_donchian_m,
        )

        for bar in enriched_bars:
            if position_state.is_open:
                position_state.stop_loss = (
                    max(position_state.stop_loss or 0.0, bar.close - self.strategy.config.risk_coefficient_k * bar.atr)
                    if bar.atr > 0
                    else position_state.stop_loss
                )

            decision = self.strategy.generate_signal(bar, position_state, account_state)
            risk_result = self.risk_engine.validate(account_state, decision)
            if not risk_result.allowed and decision.signal != SignalType.LONG_EXIT:
                self._mark_to_market(account_state, position_state, bar.close)
                equity_curve.append(account_state.equity)
                continue

            execution = self.execution_engine.execute(
                timestamp=bar.timestamp,
                symbol=symbol,
                market_price=bar.close,
                account_state=account_state,
                position_state=position_state,
                decision=decision,
            )
            account_state = execution.account_state
            position_state = execution.position_state
            if execution.fill_event:
                if execution.fill_event.side == "SELL" and execution.fill_event.pnl > 0:
                    winning_trades += 1
                trades.append(
                    {
                        "timestamp": execution.fill_event.timestamp.isoformat(),
                        "side": execution.fill_event.side,
                        "price": round(execution.fill_event.price, 4),
                        "quantity": execution.fill_event.quantity,
                        "reason": execution.fill_event.reason,
                        "pnl": round(execution.fill_event.pnl, 4),
                    }
                )

            self._mark_to_market(account_state, position_state, bar.close)
            equity_curve.append(account_state.equity)

        if position_state.is_open and enriched_bars:
            final_bar = enriched_bars[-1]
            decision = self.strategy.generate_signal(final_bar, position_state, account_state)
            decision.signal = SignalType.LONG_EXIT
            decision.reason = "forced close at end of backtest"
            execution = self.execution_engine.execute(
                timestamp=final_bar.timestamp,
                symbol=symbol,
                market_price=final_bar.close,
                account_state=account_state,
                position_state=position_state,
                decision=decision,
            )
            account_state = execution.account_state
            position_state = execution.position_state
            if execution.fill_event and execution.fill_event.pnl > 0:
                winning_trades += 1
            if execution.fill_event:
                trades.append(
                    {
                        "timestamp": execution.fill_event.timestamp.isoformat(),
                        "side": execution.fill_event.side,
                        "price": round(execution.fill_event.price, 4),
                        "quantity": execution.fill_event.quantity,
                        "reason": execution.fill_event.reason,
                        "pnl": round(execution.fill_event.pnl, 4),
                    }
                )
            self._mark_to_market(account_state, position_state, final_bar.close)

        metrics = self._calculate_metrics(initial_equity, account_state.equity, equity_curve, trades, winning_trades)
        return BacktestRunResult(
            symbol=symbol,
            bars_processed=len(enriched_bars),
            metrics=metrics,
            trades=trades,
            account={
                "cash": round(account_state.cash, 4),
                "equity": round(account_state.equity, 4),
                "realized_pnl": round(account_state.realized_pnl, 4),
                "unrealized_pnl": round(account_state.unrealized_pnl, 4),
                "open_positions": account_state.open_positions,
            },
        )

    @staticmethod
    def _mark_to_market(account_state: AccountState, position_state: PositionState, market_price: float) -> None:
        market_value = position_state.quantity * market_price
        unrealized = 0.0
        if position_state.is_open:
            unrealized = (market_price - position_state.entry_price) * position_state.quantity
            position_state.market_price = market_price
        account_state.unrealized_pnl = unrealized
        account_state.equity = account_state.cash + market_value
        account_state.exposure_pct = market_value / account_state.equity if account_state.equity > 0 else 0.0
        account_state.open_positions = 1 if position_state.is_open else 0

    @staticmethod
    def _calculate_metrics(
        initial_equity: float,
        ending_equity: float,
        equity_curve: list[float],
        trades: list[dict[str, str | float | int]],
        winning_trades: int,
    ) -> BacktestMetrics:
        peak = equity_curve[0] if equity_curve else initial_equity
        max_drawdown = 0.0
        for value in equity_curve:
            peak = max(peak, value)
            if peak > 0:
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)

        completed_trades = len([trade for trade in trades if trade["side"] == "SELL"])
        win_rate = winning_trades / completed_trades if completed_trades else 0.0
        return BacktestMetrics(
            total_return_pct=round((ending_equity - initial_equity) / initial_equity * 100, 4),
            max_drawdown_pct=round(max_drawdown * 100, 4),
            win_rate_pct=round(win_rate * 100, 4),
            total_trades=completed_trades,
            ending_equity=round(ending_equity, 4),
        )
