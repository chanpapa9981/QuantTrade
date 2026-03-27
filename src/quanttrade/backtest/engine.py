"""回测引擎。

这是项目里最核心的业务编排模块之一。
它会把：
1. 行情数据；
2. 策略决策；
3. 风控检查；
4. 模拟执行；
5. 审计日志；
6. 指标计算；
全部串成一次完整的历史回放流程。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from uuid import uuid4

from quanttrade.core.types import (
    AccountState,
    BacktestMetrics,
    BacktestRunResult,
    MarketBar,
    OrderEvent,
    OrderStatus,
    PendingOrderState,
    PositionState,
    SignalType,
    StrategyDecision,
)
from quanttrade.data.indicators import enrich_market_bars
from quanttrade.execution.simulator import SimulatedExecutionEngine
from quanttrade.risk.engine import RiskEngine
from quanttrade.strategies.base import Strategy


@dataclass(slots=True)
class BacktestStepResult:
    """单步样例回测结果。"""

    signal: str
    reason: str
    risk_allowed: bool
    execution_reason: str
    position_quantity: int


class BacktestEngine:
    """负责执行单步回测和完整序列回测。"""

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
        """执行一次单 bar 回测，主要用于样例链路和快速检查。"""
        decision = self.strategy.generate_signal(market_bar, position_state, account_state)
        risk_result = self.risk_engine.validate(account_state, decision, market_bar)

        # 对入场信号来说，只要风控不通过，就不允许继续执行。
        # 但对退出信号，通常宁可先退出，也不要被风控拦住。
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
            order_id="sample-order",
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
        """执行一整段历史序列回测。"""
        symbol = self.strategy.config.symbol
        account_state = AccountState(equity=initial_equity, cash=initial_equity)
        position_state = PositionState(symbol=symbol)
        pending_order: PendingOrderState | None = None
        trades: list[dict[str, str | float | int]] = []
        orders: list[dict[str, str | float | int]] = []
        audit_log: list[dict[str, str | float | int]] = []
        equity_curve: list[float] = [initial_equity]
        equity_timeline: list[dict[str, str | float]] = []
        drawdown_timeline: list[dict[str, str | float]] = []
        period_returns: list[float] = []

        # 先补齐 ATR、ADX、唐奇安通道等指标，后面策略层可直接读取。
        enriched_bars = enrich_market_bars(
            bars=bars,
            atr_period=self.strategy.config.atr_smooth_period,
            adx_period=self.strategy.config.atr_smooth_period,
            entry_donchian_n=self.strategy.config.entry_donchian_n,
            exit_donchian_m=self.strategy.config.exit_donchian_m,
        )

        for bar in enriched_bars:
            prior_equity = account_state.equity
            if position_state.is_open:
                # 持仓期间持续抬高止损，模拟趋势策略的动态保护逻辑。
                position_state.stop_loss = (
                    max(position_state.stop_loss or 0.0, bar.close - self.strategy.config.risk_coefficient_k * bar.atr)
                    if bar.atr > 0
                    else position_state.stop_loss
                )

            if pending_order:
                # 只要还有挂单，就优先处理挂单，而不是让策略重新发一张新单。
                pending_order.bars_open += 1
                if pending_order.bars_open > self.execution_engine.config.open_order_timeout_bars:
                    # 超过等待阈值后，主动取消，避免订单无限悬挂。
                    cancel_event = OrderEvent(
                        timestamp=bar.timestamp,
                        order_id=pending_order.order_id,
                        symbol=symbol,
                        side=pending_order.side,
                        status=OrderStatus.CANCELLED,
                        quantity=pending_order.remaining_quantity,
                        requested_price=bar.close,
                        filled_quantity=0,
                        remaining_quantity=pending_order.remaining_quantity,
                        broker_status="cancelled",
                        status_detail="timeout_cancelled",
                        reason="order cancelled after timeout waiting across bars",
                    )
                    orders.append(self._serialize_order_event(cancel_event))
                    audit_log.append(
                        {
                            "timestamp": bar.timestamp.isoformat(),
                            "event": "order_cancelled",
                            "signal": "long_entry" if pending_order.side == "BUY" else "long_exit",
                            "reason": "order cancelled after timeout waiting across bars",
                            "risk_allowed": 1,
                        }
                    )
                    pending_order = None
                    self._mark_to_market(account_state, position_state, bar.close)
                    equity_curve.append(account_state.equity)
                    period_returns.append(self._period_return(prior_equity, account_state.equity))
                    self._append_curves(equity_timeline, drawdown_timeline, equity_curve, bar.timestamp.isoformat(), account_state.equity)
                    continue

                if round(pending_order.requested_price, 4) != round(bar.close, 4):
                    # 如果市场已经明显变了，就记录一条 replaced 事件，表示订单被重定价。
                    replace_event = OrderEvent(
                        timestamp=bar.timestamp,
                        order_id=pending_order.order_id,
                        symbol=symbol,
                        side=pending_order.side,
                        status=OrderStatus.REPLACED,
                        quantity=pending_order.remaining_quantity,
                        requested_price=bar.close,
                        filled_quantity=0,
                        remaining_quantity=pending_order.remaining_quantity,
                        broker_status="replaced",
                        status_detail="repriced_to_bar_close",
                        reason="order repriced to current bar close while waiting for liquidity",
                    )
                    orders.append(self._serialize_order_event(replace_event))
                    audit_log.append(
                        {
                            "timestamp": bar.timestamp.isoformat(),
                            "event": "order_replaced",
                            "signal": "long_entry" if pending_order.side == "BUY" else "long_exit",
                            "reason": "order repriced to current bar close while waiting for liquidity",
                            "risk_allowed": 1,
                        }
                    )
                    pending_order.requested_price = bar.close

                execution = self.execution_engine.execute(
                    timestamp=bar.timestamp,
                    order_id=pending_order.order_id,
                    symbol=symbol,
                    market_price=bar.close,
                    market_volume=bar.volume,
                    account_state=account_state,
                    position_state=position_state,
                    decision=StrategyDecision(
                        signal=SignalType.LONG_ENTRY if pending_order.side == "BUY" else SignalType.LONG_EXIT,
                        reason=pending_order.reason,
                        stop_loss=pending_order.stop_loss,
                        quantity=pending_order.remaining_quantity,
                    ),
                    allow_existing_position=True,
                )
                account_state = execution.account_state
                position_state = execution.position_state
                pending_order = self._consume_execution(
                    execution=execution,
                    decision_signal=SignalType.LONG_ENTRY if pending_order.side == "BUY" else SignalType.LONG_EXIT,
                    orders=orders,
                    trades=trades,
                    audit_log=audit_log,
                    pending_order=pending_order,
                )
                self._mark_to_market(account_state, position_state, bar.close)
                equity_curve.append(account_state.equity)
                period_returns.append(self._period_return(prior_equity, account_state.equity))
                self._append_curves(equity_timeline, drawdown_timeline, equity_curve, bar.timestamp.isoformat(), account_state.equity)
                continue

            decision = self.strategy.generate_signal(bar, position_state, account_state)
            risk_result = self.risk_engine.validate(account_state, decision, bar)
            # 不论最终是否下单，都先把“这次策略怎么想的”写进审计日志。
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
                    # 被风控拦下的入场信号也要记成订单事件，否则事后很难知道“为什么没下单”。
                    orders.append(
                        {
                            "timestamp": bar.timestamp.isoformat(),
                            "order_id": "",
                            "side": "BUY" if decision.signal == SignalType.LONG_ENTRY else "SELL",
                            "status": OrderStatus.SKIPPED.value,
                            "quantity": decision.quantity,
                            "filled_quantity": 0,
                            "remaining_quantity": decision.quantity,
                            "broker_status": "local_skipped",
                            "status_detail": "risk_check_blocked",
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

            if decision.signal == SignalType.HOLD:
                # HOLD 代表这一根 bar 没有新动作，只做账户市值更新。
                self._mark_to_market(account_state, position_state, bar.close)
                equity_curve.append(account_state.equity)
                period_returns.append(self._period_return(prior_equity, account_state.equity))
                self._append_curves(equity_timeline, drawdown_timeline, equity_curve, bar.timestamp.isoformat(), account_state.equity)
                continue

            order_id = str(uuid4())
            # 每次真实发单前先写入 created 事件，确保订单生命周期从创建开始可追踪。
            created_event = OrderEvent(
                timestamp=bar.timestamp,
                order_id=order_id,
                symbol=symbol,
                side="BUY" if decision.signal == SignalType.LONG_ENTRY else "SELL",
                status=OrderStatus.CREATED,
                quantity=decision.quantity if decision.signal == SignalType.LONG_ENTRY else position_state.quantity,
                requested_price=bar.close,
                filled_quantity=0,
                remaining_quantity=decision.quantity if decision.signal == SignalType.LONG_ENTRY else position_state.quantity,
                broker_status="pending_new",
                status_detail="initial_submit",
                reason=decision.reason,
            )
            orders.append(self._serialize_order_event(created_event))
            audit_log.append(
                {
                    "timestamp": bar.timestamp.isoformat(),
                    "event": "order_created",
                    "signal": decision.signal.value,
                    "reason": decision.reason,
                    "risk_allowed": 1,
                }
            )
            execution = self.execution_engine.execute(
                timestamp=bar.timestamp,
                order_id=order_id,
                symbol=symbol,
                market_price=bar.close,
                market_volume=bar.volume,
                account_state=account_state,
                position_state=position_state,
                decision=decision,
            )
            account_state = execution.account_state
            position_state = execution.position_state
            requested_quantity = created_event.quantity
            pending_order = self._consume_execution(
                execution=execution,
                decision_signal=decision.signal,
                orders=orders,
                trades=trades,
                audit_log=audit_log,
                pending_order=PendingOrderState(
                    order_id=order_id,
                    symbol=symbol,
                    side="BUY" if decision.signal == SignalType.LONG_ENTRY else "SELL",
                    requested_quantity=requested_quantity,
                    remaining_quantity=requested_quantity,
                    reason=decision.reason,
                    requested_price=bar.close,
                    submitted_at=bar.timestamp,
                    stop_loss=decision.stop_loss,
                ),
            )

            self._mark_to_market(account_state, position_state, bar.close)
            equity_curve.append(account_state.equity)
            period_returns.append(self._period_return(prior_equity, account_state.equity))
            self._append_curves(equity_timeline, drawdown_timeline, equity_curve, bar.timestamp.isoformat(), account_state.equity)

        if pending_order and enriched_bars:
            # 回测结束时如果还有挂单，必须明确取消，不能把状态留在 open。
            final_bar = enriched_bars[-1]
            cancel_event = OrderEvent(
                timestamp=final_bar.timestamp,
                order_id=pending_order.order_id,
                symbol=symbol,
                side=pending_order.side,
                status=OrderStatus.CANCELLED,
                quantity=pending_order.remaining_quantity,
                requested_price=final_bar.close,
                filled_quantity=0,
                remaining_quantity=pending_order.remaining_quantity,
                broker_status="cancelled",
                status_detail="backtest_ended_with_open_order",
                reason="backtest ended with open order",
            )
            orders.append(self._serialize_order_event(cancel_event))
            audit_log.append(
                {
                    "timestamp": final_bar.timestamp.isoformat(),
                    "event": "order_cancelled",
                    "signal": "long_entry" if pending_order.side == "BUY" else "long_exit",
                    "reason": "backtest ended with open order",
                    "risk_allowed": 1,
                }
            )
            pending_order = None

        if position_state.is_open and enriched_bars:
            # 回测收尾时强制平仓，避免“回测结束但仓位还没结算”导致指标失真。
            final_bar = enriched_bars[-1]
            decision = self.strategy.generate_signal(final_bar, position_state, account_state)
            decision.signal = SignalType.LONG_EXIT
            decision.reason = "forced close at end of backtest"
            order_id = str(uuid4())
            orders.append(
                self._serialize_order_event(
                    OrderEvent(
                        timestamp=final_bar.timestamp,
                        order_id=order_id,
                        symbol=symbol,
                        side="SELL",
                        status=OrderStatus.CREATED,
                        quantity=position_state.quantity,
                        requested_price=final_bar.close,
                        filled_quantity=0,
                        remaining_quantity=position_state.quantity,
                        broker_status="pending_new",
                        status_detail="forced_close_submit",
                        reason=decision.reason,
                    )
                )
            )
            execution = self.execution_engine.execute(
                timestamp=final_bar.timestamp,
                order_id=order_id,
                symbol=symbol,
                market_price=final_bar.close,
                market_volume=final_bar.volume,
                account_state=account_state,
                position_state=position_state,
                decision=decision,
                force_full_fill=True,
            )
            account_state = execution.account_state
            position_state = execution.position_state
            self._consume_execution(
                execution=execution,
                decision_signal=decision.signal,
                orders=orders,
                trades=trades,
                audit_log=audit_log,
                pending_order=None,
            )
            self._mark_to_market(account_state, position_state, final_bar.close)
            self._append_curves(
                equity_timeline,
                drawdown_timeline,
                equity_curve + [account_state.equity],
                final_bar.timestamp.isoformat(),
                account_state.equity,
            )

        # 所有订单、成交和净值序列都准备好之后，再统一计算回测指标。
        metrics = self._calculate_metrics(
            initial_equity,
            account_state.equity,
            equity_curve,
            period_returns,
            trades,
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

    def _consume_execution(
        self,
        execution: object,
        decision_signal: SignalType,
        orders: list[dict[str, str | float | int]],
        trades: list[dict[str, str | float | int]],
        audit_log: list[dict[str, str | float | int]],
        pending_order: PendingOrderState | None,
    ) -> PendingOrderState | None:
        """把执行层结果吸收到回测上下文中。

        这个方法的作用是把订单事件、成交事件、审计日志和 pending order 状态同步更新，
        避免主循环里到处重复写同样的收尾逻辑。
        """
        next_pending = pending_order
        if execution.order_events:
            orders.extend([self._serialize_order_event(event) for event in execution.order_events])
            last_event = execution.order_events[-1]
            audit_log.append(
                {
                    "timestamp": last_event.timestamp.isoformat(),
                    "event": "order_" + last_event.status.value,
                    "signal": decision_signal.value,
                    "reason": execution.reason,
                    "risk_allowed": 1,
                }
            )
            if last_event.status == OrderStatus.FILLED:
                next_pending = None
            elif last_event.status in {OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED} and pending_order is not None:
                next_pending.remaining_quantity = last_event.remaining_quantity
            elif last_event.status in {OrderStatus.REJECTED, OrderStatus.CANCELLED}:
                next_pending = None
        for fill_event in execution.fill_events:
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
        return next_pending

    @staticmethod
    def _serialize_order_event(event: OrderEvent) -> dict[str, str | float | int]:
        """把 dataclass 形式的订单事件转成便于 JSON/数据库处理的字典。"""
        return {
            "timestamp": event.timestamp.isoformat(),
            "order_id": event.order_id,
            "side": event.side,
            "status": event.status.value,
            "quantity": event.quantity,
            "filled_quantity": event.filled_quantity,
            "remaining_quantity": event.remaining_quantity,
            "broker_status": event.broker_status,
            "status_detail": event.status_detail,
            "requested_price": round(event.requested_price, 4),
            "fill_price": round(event.fill_price, 4),
            "commission": round(event.commission, 4),
            "gross_value": round(event.gross_value, 4),
            "net_value": round(event.net_value, 4),
            "reason": event.reason,
        }

    @staticmethod
    def _mark_to_market(account_state: AccountState, position_state: PositionState, market_price: float) -> None:
        """按最新市场价格更新账户权益和未实现盈亏。"""
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
        """往净值曲线和回撤曲线中追加当前时点。"""
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
    ) -> BacktestMetrics:
        """根据完整回测过程计算绩效指标。"""
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

        # 对当前这套单边做多策略来说，一笔交易是否真正结束，以 SELL 成交为准。
        closing_trades = [trade for trade in trades if trade["side"] == "SELL"]
        completed_trades = len(closing_trades)
        winning_trades = sum(1 for trade in closing_trades if float(trade.get("pnl", 0.0)) > 0)
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
        """计算相邻两个时点之间的收益率。"""
        if prior_equity <= 0:
            return 0.0
        return (current_equity - prior_equity) / prior_equity

    @staticmethod
    def _sharpe_ratio(period_returns: list[float]) -> float:
        """计算 Sharpe 比率。"""
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
        """计算 Sortino 比率，只把下行波动当成风险。"""
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
