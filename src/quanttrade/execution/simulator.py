from __future__ import annotations

from dataclasses import dataclass

from quanttrade.config.models import ExecutionConfig
from quanttrade.core.types import AccountState, FillEvent, OrderEvent, OrderStatus, PositionState, SignalType, StrategyDecision


@dataclass(slots=True)
class ExecutionResult:
    accepted: bool
    reason: str
    account_state: AccountState
    position_state: PositionState
    fill_event: FillEvent | None = None
    order_event: OrderEvent | None = None


class SimulatedExecutionEngine:
    def __init__(self, config: ExecutionConfig) -> None:
        self.config = config

    def _apply_slippage(self, market_price: float, side: str) -> float:
        slippage_multiplier = self.config.simulated_slippage_bps / 10_000
        if side == "BUY":
            return round(market_price * (1 + slippage_multiplier), 4)
        return round(market_price * (1 - slippage_multiplier), 4)

    def _commission(self, quantity: int) -> float:
        return round(
            max(
                self.config.min_commission,
                self.config.commission_per_order + quantity * self.config.commission_per_share,
            ),
            4,
        )

    def execute(
        self,
        timestamp: object,
        symbol: str,
        market_price: float,
        account_state: AccountState,
        position_state: PositionState,
        decision: StrategyDecision,
    ) -> ExecutionResult:
        if decision.signal == SignalType.LONG_ENTRY:
            fill_price = self._apply_slippage(market_price, "BUY")
            commission = self._commission(decision.quantity)
            gross_cost = decision.quantity * fill_price
            total_cost = gross_cost + commission
            if decision.quantity <= 0:
                return ExecutionResult(
                    False,
                    "entry quantity must be positive",
                    account_state,
                    position_state,
                    order_event=OrderEvent(
                        timestamp=timestamp,
                        symbol=symbol,
                        side="BUY",
                        status=OrderStatus.REJECTED,
                        quantity=decision.quantity,
                        requested_price=market_price,
                        reason="entry quantity must be positive",
                    ),
                )
            if total_cost > account_state.cash:
                return ExecutionResult(
                    False,
                    "insufficient cash for simulated entry",
                    account_state,
                    position_state,
                    order_event=OrderEvent(
                        timestamp=timestamp,
                        symbol=symbol,
                        side="BUY",
                        status=OrderStatus.REJECTED,
                        quantity=decision.quantity,
                        requested_price=market_price,
                        reason="insufficient cash for simulated entry",
                    ),
                )

            next_account = AccountState(
                equity=account_state.equity,
                cash=account_state.cash - total_cost,
                realized_pnl=account_state.realized_pnl,
                unrealized_pnl=account_state.unrealized_pnl,
                daily_pnl_pct=account_state.daily_pnl_pct,
                exposure_pct=account_state.exposure_pct,
                open_positions=1,
            )
            next_state = PositionState(
                symbol=symbol,
                quantity=decision.quantity,
                entry_price=fill_price,
                stop_loss=decision.stop_loss,
                market_price=fill_price,
            )
            fill_event = FillEvent(
                timestamp=timestamp,
                symbol=symbol,
                side="BUY",
                quantity=decision.quantity,
                price=fill_price,
                reason=decision.reason,
                commission=commission,
                gross_value=round(gross_cost, 4),
                net_value=round(total_cost, 4),
            )
            order_event = OrderEvent(
                timestamp=timestamp,
                symbol=symbol,
                side="BUY",
                status=OrderStatus.FILLED,
                quantity=decision.quantity,
                requested_price=market_price,
                fill_price=fill_price,
                commission=commission,
                gross_value=round(gross_cost, 4),
                net_value=round(total_cost, 4),
                reason=decision.reason,
            )
            return ExecutionResult(True, "simulated long entry executed", next_account, next_state, fill_event, order_event)

        if decision.signal == SignalType.LONG_EXIT:
            if not position_state.is_open:
                return ExecutionResult(
                    False,
                    "cannot exit without an open position",
                    account_state,
                    position_state,
                    order_event=OrderEvent(
                        timestamp=timestamp,
                        symbol=symbol,
                        side="SELL",
                        status=OrderStatus.REJECTED,
                        quantity=0,
                        requested_price=market_price,
                        reason="cannot exit without an open position",
                    ),
                )
            fill_price = self._apply_slippage(market_price, "SELL")
            commission = self._commission(position_state.quantity)
            gross_proceeds = position_state.quantity * fill_price
            net_proceeds = gross_proceeds - commission
            pnl = net_proceeds - position_state.quantity * position_state.entry_price
            next_account = AccountState(
                equity=account_state.equity,
                cash=account_state.cash + net_proceeds,
                realized_pnl=account_state.realized_pnl + pnl,
                unrealized_pnl=0.0,
                daily_pnl_pct=account_state.daily_pnl_pct,
                exposure_pct=0.0,
                open_positions=0,
            )
            next_state = PositionState(symbol=symbol)
            fill_event = FillEvent(
                timestamp=timestamp,
                symbol=symbol,
                side="SELL",
                quantity=position_state.quantity,
                price=fill_price,
                reason=decision.reason,
                commission=commission,
                gross_value=round(gross_proceeds, 4),
                net_value=round(net_proceeds, 4),
                pnl=round(pnl, 4),
            )
            order_event = OrderEvent(
                timestamp=timestamp,
                symbol=symbol,
                side="SELL",
                status=OrderStatus.FILLED,
                quantity=position_state.quantity,
                requested_price=market_price,
                fill_price=fill_price,
                commission=commission,
                gross_value=round(gross_proceeds, 4),
                net_value=round(net_proceeds, 4),
                reason=decision.reason,
            )
            return ExecutionResult(True, "simulated exit executed", next_account, next_state, fill_event, order_event)

        return ExecutionResult(True, "no-op", account_state, position_state)
