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
    fill_events: list[FillEvent]
    order_events: list[OrderEvent]


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

    def _liquidity_capacity(self, market_volume: float) -> int:
        return max(int(market_volume * self.config.max_fill_ratio_per_bar), 0)

    def execute(
        self,
        timestamp: object,
        symbol: str,
        market_price: float,
        market_volume: float,
        account_state: AccountState,
        position_state: PositionState,
        decision: StrategyDecision,
    ) -> ExecutionResult:
        if decision.signal == SignalType.LONG_ENTRY:
            if position_state.is_open:
                return ExecutionResult(
                    False,
                    "duplicate long entry while position already open",
                    account_state,
                    position_state,
                    fill_events=[],
                    order_events=[
                        OrderEvent(
                            timestamp=timestamp,
                            symbol=symbol,
                            side="BUY",
                            status=OrderStatus.REJECTED,
                            quantity=decision.quantity,
                            requested_price=market_price,
                            reason="duplicate long entry while position already open",
                        )
                    ],
                )
            fill_price = self._apply_slippage(market_price, "BUY")
            if decision.quantity <= 0:
                return ExecutionResult(
                    False,
                    "entry quantity must be positive",
                    account_state,
                    position_state,
                    fill_events=[],
                    order_events=[
                        OrderEvent(
                            timestamp=timestamp,
                            symbol=symbol,
                            side="BUY",
                            status=OrderStatus.REJECTED,
                            quantity=decision.quantity,
                            requested_price=market_price,
                            reason="entry quantity must be positive",
                        )
                    ],
                )
            liquidity_quantity = self._liquidity_capacity(market_volume)
            affordable_quantity = max(int((account_state.cash - self.config.min_commission) / fill_price), 0)
            executable_quantity = min(decision.quantity, liquidity_quantity, affordable_quantity)
            if executable_quantity <= 0:
                return ExecutionResult(
                    False,
                    "insufficient cash or liquidity for simulated entry",
                    account_state,
                    position_state,
                    fill_events=[],
                    order_events=[
                        OrderEvent(
                            timestamp=timestamp,
                            symbol=symbol,
                            side="BUY",
                            status=OrderStatus.REJECTED,
                            quantity=decision.quantity,
                            requested_price=market_price,
                            reason="insufficient cash or liquidity for simulated entry",
                        )
                    ],
                )
            commission = self._commission(executable_quantity)
            gross_cost = executable_quantity * fill_price
            total_cost = gross_cost + commission

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
                quantity=executable_quantity,
                entry_price=fill_price,
                stop_loss=decision.stop_loss,
                market_price=fill_price,
            )
            fill_event = FillEvent(
                timestamp=timestamp,
                symbol=symbol,
                side="BUY",
                quantity=executable_quantity,
                price=fill_price,
                reason=decision.reason,
                commission=commission,
                gross_value=round(gross_cost, 4),
                net_value=round(total_cost, 4),
            )
            remaining_quantity = max(decision.quantity - executable_quantity, 0)
            order_events = [
                OrderEvent(
                    timestamp=timestamp,
                    symbol=symbol,
                    side="BUY",
                    status=OrderStatus.FILLED if remaining_quantity == 0 else OrderStatus.PARTIALLY_FILLED,
                    quantity=decision.quantity,
                    requested_price=market_price,
                    filled_quantity=executable_quantity,
                    remaining_quantity=remaining_quantity,
                    fill_price=fill_price,
                    commission=commission,
                    gross_value=round(gross_cost, 4),
                    net_value=round(total_cost, 4),
                    reason=decision.reason if remaining_quantity == 0 else "partially filled due to simulated liquidity/cash cap",
                )
            ]
            if remaining_quantity > 0:
                order_events.append(
                    OrderEvent(
                        timestamp=timestamp,
                        symbol=symbol,
                        side="BUY",
                        status=OrderStatus.CANCELLED,
                        quantity=remaining_quantity,
                        requested_price=market_price,
                        filled_quantity=0,
                        remaining_quantity=remaining_quantity,
                        reason="remaining quantity cancelled after partial fill",
                    )
                )
            return ExecutionResult(
                True,
                "simulated long entry executed" if remaining_quantity == 0 else "simulated long entry partially executed",
                next_account,
                next_state,
                fill_events=[fill_event],
                order_events=order_events,
            )

        if decision.signal == SignalType.LONG_EXIT:
            if not position_state.is_open:
                return ExecutionResult(
                    False,
                    "cannot exit without an open position",
                    account_state,
                    position_state,
                    fill_events=[],
                    order_events=[
                        OrderEvent(
                            timestamp=timestamp,
                            symbol=symbol,
                            side="SELL",
                            status=OrderStatus.REJECTED,
                            quantity=0,
                            requested_price=market_price,
                            reason="cannot exit without an open position",
                        )
                    ],
                )
            fill_price = self._apply_slippage(market_price, "SELL")
            liquidity_quantity = self._liquidity_capacity(market_volume)
            executable_quantity = min(position_state.quantity, liquidity_quantity)
            if executable_quantity <= 0:
                return ExecutionResult(
                    False,
                    "insufficient liquidity for simulated exit",
                    account_state,
                    position_state,
                    fill_events=[],
                    order_events=[
                        OrderEvent(
                            timestamp=timestamp,
                            symbol=symbol,
                            side="SELL",
                            status=OrderStatus.CANCELLED,
                            quantity=position_state.quantity,
                            requested_price=market_price,
                            remaining_quantity=position_state.quantity,
                            reason="exit cancelled because no simulated liquidity was available",
                        )
                    ],
                )
            commission = self._commission(executable_quantity)
            gross_proceeds = executable_quantity * fill_price
            net_proceeds = gross_proceeds - commission
            pnl = net_proceeds - executable_quantity * position_state.entry_price
            remaining_quantity = max(position_state.quantity - executable_quantity, 0)
            next_account = AccountState(
                equity=account_state.equity,
                cash=account_state.cash + net_proceeds,
                realized_pnl=account_state.realized_pnl + pnl,
                unrealized_pnl=0.0,
                daily_pnl_pct=account_state.daily_pnl_pct,
                exposure_pct=account_state.exposure_pct,
                open_positions=1 if remaining_quantity > 0 else 0,
            )
            next_state = (
                PositionState(
                    symbol=symbol,
                    quantity=remaining_quantity,
                    entry_price=position_state.entry_price,
                    stop_loss=position_state.stop_loss,
                    market_price=fill_price,
                )
                if remaining_quantity > 0
                else PositionState(symbol=symbol)
            )
            fill_event = FillEvent(
                timestamp=timestamp,
                symbol=symbol,
                side="SELL",
                quantity=executable_quantity,
                price=fill_price,
                reason=decision.reason,
                commission=commission,
                gross_value=round(gross_proceeds, 4),
                net_value=round(net_proceeds, 4),
                pnl=round(pnl, 4),
            )
            order_events = [
                OrderEvent(
                    timestamp=timestamp,
                    symbol=symbol,
                    side="SELL",
                    status=OrderStatus.FILLED if remaining_quantity == 0 else OrderStatus.PARTIALLY_FILLED,
                    quantity=position_state.quantity,
                    requested_price=market_price,
                    filled_quantity=executable_quantity,
                    remaining_quantity=remaining_quantity,
                    fill_price=fill_price,
                    commission=commission,
                    gross_value=round(gross_proceeds, 4),
                    net_value=round(net_proceeds, 4),
                    reason=decision.reason if remaining_quantity == 0 else "partially filled due to simulated liquidity cap",
                )
            ]
            if remaining_quantity > 0:
                order_events.append(
                    OrderEvent(
                        timestamp=timestamp,
                        symbol=symbol,
                        side="SELL",
                        status=OrderStatus.CANCELLED,
                        quantity=remaining_quantity,
                        requested_price=market_price,
                        filled_quantity=0,
                        remaining_quantity=remaining_quantity,
                        reason="remaining quantity cancelled after partial exit fill",
                    )
                )
            return ExecutionResult(
                True,
                "simulated exit executed" if remaining_quantity == 0 else "simulated exit partially executed",
                next_account,
                next_state,
                fill_events=[fill_event],
                order_events=order_events,
            )

        return ExecutionResult(True, "no-op", account_state, position_state, fill_events=[], order_events=[])
