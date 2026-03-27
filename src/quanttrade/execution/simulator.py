from __future__ import annotations

from dataclasses import dataclass

from quanttrade.core.types import AccountState, FillEvent, PositionState, SignalType, StrategyDecision


@dataclass(slots=True)
class ExecutionResult:
    accepted: bool
    reason: str
    account_state: AccountState
    position_state: PositionState
    fill_event: FillEvent | None = None


class SimulatedExecutionEngine:
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
            cost = decision.quantity * market_price
            if decision.quantity <= 0:
                return ExecutionResult(False, "entry quantity must be positive", account_state, position_state)
            if cost > account_state.cash:
                return ExecutionResult(False, "insufficient cash for simulated entry", account_state, position_state)

            next_account = AccountState(
                equity=account_state.equity,
                cash=account_state.cash - cost,
                realized_pnl=account_state.realized_pnl,
                unrealized_pnl=account_state.unrealized_pnl,
                daily_pnl_pct=account_state.daily_pnl_pct,
                exposure_pct=account_state.exposure_pct,
                open_positions=1,
            )
            next_state = PositionState(
                symbol=symbol,
                quantity=decision.quantity,
                entry_price=market_price,
                stop_loss=decision.stop_loss,
                market_price=market_price,
            )
            fill_event = FillEvent(
                timestamp=timestamp,
                symbol=symbol,
                side="BUY",
                quantity=decision.quantity,
                price=market_price,
                reason=decision.reason,
            )
            return ExecutionResult(True, "simulated long entry executed", next_account, next_state, fill_event)

        if decision.signal == SignalType.LONG_EXIT:
            if not position_state.is_open:
                return ExecutionResult(False, "cannot exit without an open position", account_state, position_state)
            proceeds = position_state.quantity * market_price
            pnl = proceeds - position_state.quantity * position_state.entry_price
            next_account = AccountState(
                equity=account_state.equity,
                cash=account_state.cash + proceeds,
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
                price=market_price,
                reason=decision.reason,
                pnl=round(pnl, 4),
            )
            return ExecutionResult(True, "simulated exit executed", next_account, next_state, fill_event)

        return ExecutionResult(True, "no-op", account_state, position_state)
