from __future__ import annotations

from quanttrade.config.models import RiskConfig
from quanttrade.core.types import AccountState, StrategyDecision
from quanttrade.risk.base import RiskCheckResult


class RiskEngine:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def validate(self, account_state: AccountState, decision: StrategyDecision) -> RiskCheckResult:
        if decision.quantity < 0:
            return RiskCheckResult(allowed=False, reason="negative order quantity is invalid")
        if account_state.daily_pnl_pct <= -self.config.max_daily_drawdown:
            return RiskCheckResult(allowed=False, reason="daily drawdown circuit breaker triggered")
        if account_state.exposure_pct >= self.config.global_max_exposure and decision.quantity > 0:
            return RiskCheckResult(allowed=False, reason="global exposure limit reached")
        if account_state.open_positions >= self.config.max_open_positions and decision.quantity > 0:
            return RiskCheckResult(allowed=False, reason="max open positions reached")
        if decision.quantity == 0 and decision.signal.value.endswith("entry"):
            return RiskCheckResult(allowed=False, reason="position size rounded down to zero")
        return RiskCheckResult(allowed=True, reason="risk checks passed")
