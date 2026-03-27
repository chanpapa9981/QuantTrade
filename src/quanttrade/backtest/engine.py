from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt

from quanttrade.core.types import (
    AccountState,
    BacktestMetrics,
    BacktestRunResult,
    MarketBar,
    OrderStatus,
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
    def __init__(self, strategy: Strategy, risk_engine: RiskEngine, execution_engine: SimulatedExecutionEngine) -> None:
        self.strategy = strategy
        self.risk_engine = risk_engine
        self.execution_engine = execution_engine

    def run_once(
        self,
        market_bar: MarketBar,
        account_state: AccountState,
        position_state: PositionState,
    ) -> BacktestStepResult:
        decision = self.strategy.generate_signal(market_bar, position_state, account_state)
        risk_result = self.risk_engine.validate(account_state, decision, market_bar)

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
            market_volume=market_bar.volume,
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
        orders: list[dict[str, str | float | int]] = []
        audit_log: list[dict[str, str | float | int]] = []
        equity_curve: list[float] = [initial_equity]
        equity_timeline: list[dict[str, str | float]] = []
        drawdown_timeline: list[dict[str, str | float]] = []
        winning_trades = 0
        period_returns: list[float] = []

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
            prior_equity = account_state.equity
            risk_result = self.risk_engine.validate(account_state, decision, bar)
            audit_log.append(
                {
                    "timestamp": bar.timestamp.isoformat(),
                    "event": "signal_evaluated",
                    "signal": decision.signal.value,
                    "reason": decision.reason,
                    "risk_allowed": int(risk_result.allowed),
                }
            )
            if not risk_result.allowed and decision.signal != SignalType.LONG_EXIT:
                if decision.signal != SignalType.HOLD:
                    orders.append(
                        {
                            "timestamp": bar.timestamp.isoformat(),
                            "side": "BUY" if decision.signal == SignalType.LONG_ENTRY else "SELL",
                            "status": OrderStatus.SKIPPED.value,
                            "quantity": decision.quantity,
                            "requested_price": round(bar.close, 4),
                            "fill_price": 0.0,
                            "commission": 0.0,
                            "net_value": 0.0,
                            "reason": risk_result.reason,
                        }
                    )
                    audit_log.append(
                        {
                            "timestamp": bar.timestamp.isoformat(),
                            "event": "order_skipped",
                            "signal": decision.signal.value,
                            "reason": risk_result.reason,
                            "risk_allowed": 0,
                        }
                    )
                self._mark_to_market(account_state, position_state, bar.close)
                equity_curve.append(account_state.equity)
                period_returns.append(self._period_return(prior_equity, account_state.equity))
                self._append_curves(equity_timeline, drawdown_timeline, equity_curve, bar.timestamp.isoformat(), account_state.equity)
                continue

            execution = self.execution_engine.execute(
                timestamp=bar.timestamp,
                symbol=symbol,
                market_price=bar.close,
                market_volume=bar.volume,
                account_state=account_state,
                position_state=position_state,
                decision=decision,
            )
            account_state = execution.account_state
            position_state = execution.position_state
            if execution.order_events:
                orders.extend(
                    [
                        {
                            "timestamp": event.timestamp.isoformat(),
                            "side": event.side,
                            "status": event.status.value,
                            "quantity": event.quantity,
                            "filled_quantity": event.filled_quantity,
                            "remaining_quantity": event.remaining_quantity,
                            "requested_price": round(event.requested_price, 4),
                            "fill_price": round(event.fill_price, 4),
                            "commission": round(event.commission, 4),
                            "gross_value": round(event.gross_value, 4),
                            "net_value": round(event.net_value, 4),
                            "reason": event.reason,
                        }
                        for event in execution.order_events
                    ]
                )
                audit_log.append(
                    {
                        "timestamp": execution.order_events[-1].timestamp.isoformat(),
                        "event": "order_" + execution.order_events[-1].status.value,
                        "signal": decision.signal.value,
                        "reason": execution.reason,
                        "risk_allowed": 1,
                    }
                )
            for fill_event in execution.fill_events:
                if fill_event.side == "SELL" and fill_event.pnl > 0:
                    winning_trades += 1
                trades.append(
                    {
                        "timestamp": fill_event.timestamp.isoformat(),
                        "side": fill_event.side,
                        "price": round(fill_event.price, 4),
                        "quantity": fill_event.quantity,
                        "reason": fill_event.reason,
                        "commission": round(fill_event.commission, 4),
                        "gross_value": round(fill_event.gross_value, 4),
                        "net_value": round(fill_event.net_value, 4),
                        "pnl": round(fill_event.pnl, 4),
                    }
                )

            self._mark_to_market(account_state, position_state, bar.close)
            equity_curve.append(account_state.equity)
            period_returns.append(self._period_return(prior_equity, account_state.equity))
            self._append_curves(equity_timeline, drawdown_timeline, equity_curve, bar.timestamp.isoformat(), account_state.equity)

        if position_state.is_open and enriched_bars:
            final_bar = enriched_bars[-1]
            decision = self.strategy.generate_signal(final_bar, position_state, account_state)
            decision.signal = SignalType.LONG_EXIT
            decision.reason = "forced close at end of backtest"
            execution = self.execution_engine.execute(
                timestamp=final_bar.timestamp,
                symbol=symbol,
                market_price=final_bar.close,
                market_volume=final_bar.volume,
                account_state=account_state,
                position_state=position_state,
                decision=decision,
            )
            account_state = execution.account_state
            position_state = execution.position_state
            if execution.order_events:
                orders.extend(
                    [
                        {
                            "timestamp": event.timestamp.isoformat(),
                            "side": event.side,
                            "status": event.status.value,
                            "quantity": event.quantity,
                            "filled_quantity": event.filled_quantity,
                            "remaining_quantity": event.remaining_quantity,
                            "requested_price": round(event.requested_price, 4),
                            "fill_price": round(event.fill_price, 4),
                            "commission": round(event.commission, 4),
                            "gross_value": round(event.gross_value, 4),
                            "net_value": round(event.net_value, 4),
                            "reason": event.reason,
                        }
                        for event in execution.order_events
                    ]
                )
                audit_log.append(
                    {
                        "timestamp": execution.order_events[-1].timestamp.isoformat(),
                        "event": "order_" + execution.order_events[-1].status.value,
                        "signal": decision.signal.value,
                        "reason": execution.reason,
                        "risk_allowed": 1,
                    }
                )
            for fill_event in execution.fill_events:
                if fill_event.pnl > 0:
                    winning_trades += 1
                trades.append(
                    {
                        "timestamp": fill_event.timestamp.isoformat(),
                        "side": fill_event.side,
                        "price": round(fill_event.price, 4),
                        "quantity": fill_event.quantity,
                        "reason": fill_event.reason,
                        "commission": round(fill_event.commission, 4),
                        "gross_value": round(fill_event.gross_value, 4),
                        "net_value": round(fill_event.net_value, 4),
                        "pnl": round(fill_event.pnl, 4),
                    }
                )
            self._mark_to_market(account_state, position_state, final_bar.close)
            self._append_curves(
                equity_timeline,
                drawdown_timeline,
                equity_curve + [account_state.equity],
                final_bar.timestamp.isoformat(),
                account_state.equity,
            )

        metrics = self._calculate_metrics(
            initial_equity,
            account_state.equity,
            equity_curve,
            period_returns,
            trades,
            winning_trades,
        )
        return BacktestRunResult(
            symbol=symbol,
            bars_processed=len(enriched_bars),
            metrics=metrics,
            trades=trades,
            orders=orders,
            audit_log=audit_log[-200:],
            account={
                "cash": round(account_state.cash, 4),
                "equity": round(account_state.equity, 4),
                "realized_pnl": round(account_state.realized_pnl, 4),
                "unrealized_pnl": round(account_state.unrealized_pnl, 4),
                "open_positions": account_state.open_positions,
            },
            equity_curve=equity_timeline,
            drawdown_curve=drawdown_timeline,
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
    def _append_curves(
        equity_timeline: list[dict[str, str | float]],
        drawdown_timeline: list[dict[str, str | float]],
        equity_curve: list[float],
        timestamp: str,
        equity_value: float,
    ) -> None:
        peak = max(equity_curve) if equity_curve else equity_value
        drawdown_pct = (peak - equity_value) / peak * 100 if peak > 0 else 0.0
        equity_timeline.append({"timestamp": timestamp, "equity": round(equity_value, 4)})
        drawdown_timeline.append({"timestamp": timestamp, "drawdown_pct": round(drawdown_pct, 4)})

    @staticmethod
    def _calculate_metrics(
        initial_equity: float,
        ending_equity: float,
        equity_curve: list[float],
        period_returns: list[float],
        trades: list[dict[str, str | float | int]],
        winning_trades: int,
    ) -> BacktestMetrics:
        peak = equity_curve[0] if equity_curve else initial_equity
        max_drawdown = 0.0
        underwater_bars = 0
        longest_underwater_bars = 0
        for value in equity_curve:
            peak = max(peak, value)
            if peak > 0:
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
                if drawdown > 0:
                    underwater_bars += 1
                    longest_underwater_bars = max(longest_underwater_bars, underwater_bars)
                else:
                    underwater_bars = 0

        closing_trades = [trade for trade in trades if trade["side"] == "SELL"]
        completed_trades = len(closing_trades)
        win_rate = winning_trades / completed_trades if completed_trades else 0.0
        losing_trades = sum(1 for trade in closing_trades if float(trade.get("pnl", 0.0)) < 0)
        total_profit = sum(float(trade.get("pnl", 0.0)) for trade in closing_trades if float(trade.get("pnl", 0.0)) > 0)
        total_loss = abs(sum(float(trade.get("pnl", 0.0)) for trade in closing_trades if float(trade.get("pnl", 0.0)) < 0))
        avg_trade_pnl = sum(float(trade.get("pnl", 0.0)) for trade in closing_trades) / completed_trades if completed_trades else 0.0
        profit_factor = total_profit / total_loss if total_loss > 0 else (float("inf") if total_profit > 0 else 0.0)
        sharpe_ratio = BacktestEngine._sharpe_ratio(period_returns)
        sortino_ratio = BacktestEngine._sortino_ratio(period_returns)
        return BacktestMetrics(
            total_return_pct=round((ending_equity - initial_equity) / initial_equity * 100, 4),
            max_drawdown_pct=round(max_drawdown * 100, 4),
            longest_underwater_bars=longest_underwater_bars,
            sharpe_ratio=round(sharpe_ratio, 4),
            sortino_ratio=round(sortino_ratio, 4),
            win_rate_pct=round(win_rate * 100, 4),
            total_trades=completed_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_trade_pnl=round(avg_trade_pnl, 4),
            profit_factor=round(profit_factor, 4) if profit_factor != float("inf") else 9999.0,
            ending_equity=round(ending_equity, 4),
        )

    @staticmethod
    def _period_return(prior_equity: float, current_equity: float) -> float:
        if prior_equity <= 0:
            return 0.0
        return (current_equity - prior_equity) / prior_equity

    @staticmethod
    def _sharpe_ratio(period_returns: list[float]) -> float:
        returns = [value for value in period_returns if value is not None]
        if len(returns) < 2:
            return 0.0
        mean_return = sum(returns) / len(returns)
        variance = sum((value - mean_return) ** 2 for value in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5
        if std_dev == 0:
            return 0.0
        return mean_return / std_dev * sqrt(len(returns))

    @staticmethod
    def _sortino_ratio(period_returns: list[float]) -> float:
        returns = [value for value in period_returns if value is not None]
        if len(returns) < 2:
            return 0.0
        mean_return = sum(returns) / len(returns)
        downside = [value for value in returns if value < 0]
        if not downside:
            return 9999.0 if mean_return > 0 else 0.0
        downside_variance = sum(value**2 for value in downside) / len(downside)
        downside_dev = downside_variance ** 0.5
        if downside_dev == 0:
            return 0.0
        return mean_return / downside_dev * sqrt(len(returns))
