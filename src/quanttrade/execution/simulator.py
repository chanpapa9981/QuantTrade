"""模拟执行引擎。

这个模块负责回答一个最现实的问题：
“策略说要买/卖，但市场和账户条件真的允许这样成交吗？”

它会处理：
1. 滑点；
2. 手续费；
3. 单根 bar 的流动性容量；
4. 部分成交；
5. 订单保持 open 等待下一根 bar。
"""

from __future__ import annotations

from dataclasses import dataclass

from quanttrade.config.models import ExecutionConfig
from quanttrade.core.types import AccountState, FillEvent, OrderEvent, OrderStatus, PositionState, SignalType, StrategyDecision


@dataclass(slots=True)
class ExecutionResult:
    """执行层返回结果。"""

    accepted: bool
    reason: str
    account_state: AccountState
    position_state: PositionState
    fill_events: list[FillEvent]
    order_events: list[OrderEvent]


class SimulatedExecutionEngine:
    """把策略决策变成模拟成交结果。"""

    def __init__(self, config: ExecutionConfig) -> None:
        self.config = config

    def _apply_slippage(self, market_price: float, side: str) -> float:
        """按照买卖方向对市场价施加滑点。"""
        slippage_multiplier = self.config.simulated_slippage_bps / 10_000
        if side == "BUY":
            return round(market_price * (1 + slippage_multiplier), 4)
        return round(market_price * (1 - slippage_multiplier), 4)

    def _commission(self, quantity: int) -> float:
        """计算这笔订单的手续费。"""
        return round(
            max(
                self.config.min_commission,
                self.config.commission_per_order + quantity * self.config.commission_per_share,
            ),
            4,
        )

    def _liquidity_capacity(self, market_volume: float) -> int:
        """估算单根 bar 最多允许成交多少股。"""
        return max(int(market_volume * self.config.max_fill_ratio_per_bar), 0)

    @staticmethod
    def _broker_status_for(status: OrderStatus) -> str:
        """把内部订单状态映射成更接近券商接口语义的状态字符串。"""
        mapping = {
            OrderStatus.CREATED: "pending_new",
            OrderStatus.OPEN: "working",
            OrderStatus.REPLACED: "replaced",
            OrderStatus.FILLED: "filled",
            OrderStatus.PARTIALLY_FILLED: "partially_filled",
            OrderStatus.CANCELLED: "cancelled",
            OrderStatus.REJECTED: "rejected",
            OrderStatus.SKIPPED: "local_skipped",
        }
        return mapping.get(status, "unknown")

    def _build_order_event(
        self,
        *,
        timestamp: object,
        order_id: str,
        symbol: str,
        side: str,
        status: OrderStatus,
        quantity: int,
        requested_price: float,
        reason: str,
        status_detail: str,
        filled_quantity: int = 0,
        remaining_quantity: int = 0,
        fill_price: float = 0.0,
        commission: float = 0.0,
        gross_value: float = 0.0,
        net_value: float = 0.0,
    ) -> OrderEvent:
        """统一构建订单事件，避免各分支漏填 broker 语义字段。"""
        return OrderEvent(
            timestamp=timestamp,
            order_id=order_id,
            symbol=symbol,
            side=side,
            status=status,
            quantity=quantity,
            requested_price=requested_price,
            filled_quantity=filled_quantity,
            remaining_quantity=remaining_quantity,
            broker_status=self._broker_status_for(status),
            status_detail=status_detail,
            fill_price=fill_price,
            commission=commission,
            gross_value=gross_value,
            net_value=net_value,
            reason=reason,
        )

    def execute(
        self,
        timestamp: object,
        order_id: str,
        symbol: str,
        market_price: float,
        market_volume: float,
        account_state: AccountState,
        position_state: PositionState,
        decision: StrategyDecision,
        allow_existing_position: bool = False,
        force_full_fill: bool = False,
    ) -> ExecutionResult:
        """执行一笔策略决策，返回账户、持仓和订单/成交事件的变化结果。"""
        if decision.signal == SignalType.LONG_ENTRY:
            # 正常情况下，不允许在已有多头持仓时再次重复开同向仓位。
            if position_state.is_open and not allow_existing_position:
                return ExecutionResult(
                    False,
                    "duplicate long entry while position already open",
                    account_state,
                    position_state,
                    fill_events=[],
                    order_events=[
                        self._build_order_event(
                            timestamp=timestamp,
                            order_id=order_id,
                            symbol=symbol,
                            side="BUY",
                            status=OrderStatus.REJECTED,
                            quantity=decision.quantity,
                            requested_price=market_price,
                            reason="duplicate long entry while position already open",
                            status_detail="duplicate_position_guard",
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
                        self._build_order_event(
                            timestamp=timestamp,
                            order_id=order_id,
                            symbol=symbol,
                            side="BUY",
                            status=OrderStatus.REJECTED,
                            quantity=decision.quantity,
                            requested_price=market_price,
                            reason="entry quantity must be positive",
                            status_detail="invalid_entry_quantity",
                        )
                    ],
                )
            # 真正能成交多少，要同时受“想买多少”“流动性允许多少”“现金买得起多少”三者约束。
            liquidity_quantity = decision.quantity if force_full_fill else self._liquidity_capacity(market_volume)
            affordable_quantity = max(int((account_state.cash - self.config.min_commission) / fill_price), 0)
            executable_quantity = min(decision.quantity, liquidity_quantity, affordable_quantity)
            if affordable_quantity <= 0:
                return ExecutionResult(
                    False,
                    "insufficient cash for simulated entry",
                    account_state,
                    position_state,
                    fill_events=[],
                    order_events=[
                        self._build_order_event(
                            timestamp=timestamp,
                            order_id=order_id,
                            symbol=symbol,
                            side="BUY",
                            status=OrderStatus.REJECTED,
                            quantity=decision.quantity,
                            requested_price=market_price,
                            reason="insufficient cash for simulated entry",
                            status_detail="insufficient_cash",
                        )
                    ],
                )
            if executable_quantity <= 0:
                # 如果当前 bar 没有可成交容量，就保留 open 状态，让回测器下一根 bar 再尝试。
                return ExecutionResult(
                    True,
                    "order remains open awaiting liquidity",
                    account_state,
                    position_state,
                    fill_events=[],
                    order_events=[
                        self._build_order_event(
                            timestamp=timestamp,
                            order_id=order_id,
                            symbol=symbol,
                            side="BUY",
                            status=OrderStatus.OPEN,
                            quantity=decision.quantity,
                            requested_price=market_price,
                            filled_quantity=0,
                            remaining_quantity=decision.quantity,
                            reason="order remains open awaiting liquidity",
                            status_detail="awaiting_entry_liquidity",
                        )
                    ],
                )
            commission = self._commission(executable_quantity)
            gross_cost = executable_quantity * fill_price
            total_cost = gross_cost + commission
            current_quantity = position_state.quantity
            next_quantity = current_quantity + executable_quantity
            # 如果是补仓，需要重新计算持仓均价。
            blended_entry_price = fill_price
            if current_quantity > 0 and next_quantity > 0:
                blended_entry_price = round(
                    ((position_state.entry_price * current_quantity) + (fill_price * executable_quantity)) / next_quantity,
                    4,
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
                quantity=next_quantity,
                entry_price=blended_entry_price,
                stop_loss=decision.stop_loss or position_state.stop_loss,
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
                self._build_order_event(
                    timestamp=timestamp,
                    order_id=order_id,
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
                    reason=decision.reason if remaining_quantity == 0 else "partially filled and left open for next bar",
                    status_detail="entry_filled_on_submit" if remaining_quantity == 0 else "entry_partial_fill_waiting",
                )
            ]
            return ExecutionResult(
                True,
                "simulated long entry executed" if remaining_quantity == 0 else "simulated long entry partially executed",
                next_account,
                next_state,
                fill_events=[fill_event],
                order_events=order_events,
            )

        if decision.signal == SignalType.LONG_EXIT:
            # 没有持仓却要求卖出，属于无效动作，直接拒绝。
            if not position_state.is_open:
                return ExecutionResult(
                    False,
                    "cannot exit without an open position",
                    account_state,
                    position_state,
                    fill_events=[],
                    order_events=[
                        self._build_order_event(
                            timestamp=timestamp,
                            order_id=order_id,
                            symbol=symbol,
                            side="SELL",
                            status=OrderStatus.REJECTED,
                            quantity=0,
                            requested_price=market_price,
                            reason="cannot exit without an open position",
                            status_detail="exit_without_position",
                        )
                    ],
                )
            fill_price = self._apply_slippage(market_price, "SELL")
            # 卖出也会受 bar 容量限制，所以可能只卖出一部分。
            liquidity_quantity = position_state.quantity if force_full_fill else self._liquidity_capacity(market_volume)
            executable_quantity = min(position_state.quantity, liquidity_quantity)
            if executable_quantity <= 0:
                return ExecutionResult(
                    True,
                    "exit order remains open awaiting liquidity",
                    account_state,
                    position_state,
                    fill_events=[],
                    order_events=[
                        self._build_order_event(
                            timestamp=timestamp,
                            order_id=order_id,
                            symbol=symbol,
                            side="SELL",
                            status=OrderStatus.OPEN,
                            quantity=position_state.quantity,
                            requested_price=market_price,
                            filled_quantity=0,
                            remaining_quantity=position_state.quantity,
                            reason="exit order remains open awaiting liquidity",
                            status_detail="awaiting_exit_liquidity",
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
                self._build_order_event(
                    timestamp=timestamp,
                    order_id=order_id,
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
                    reason=decision.reason if remaining_quantity == 0 else "partially filled and left open for next bar",
                    status_detail="exit_filled_on_submit" if remaining_quantity == 0 else "exit_partial_fill_waiting",
                )
            ]
            return ExecutionResult(
                True,
                "simulated exit executed" if remaining_quantity == 0 else "simulated exit partially executed",
                next_account,
                next_state,
                fill_events=[fill_event],
                order_events=order_events,
            )

        # HOLD 信号最终什么都不做，但仍返回一个标准结构，方便调用方统一处理。
        return ExecutionResult(True, "no-op", account_state, position_state, fill_events=[], order_events=[])
