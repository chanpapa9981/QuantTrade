from __future__ import annotations

from quanttrade.config.models import RiskConfig
from quanttrade.core.types import AccountState, MarketBar, StrategyDecision
from quanttrade.risk.base import RiskCheckResult


class RiskEngine:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def validate(
        self,
        account_state: AccountState,
        decision: StrategyDecision,
        market_bar: MarketBar | None = None,
    ) -> RiskCheckResult:
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
        if market_bar and decision.signal.value.endswith("entry"):
            if market_bar.volume < self.config.liquidity_filter:
                return RiskCheckResult(allowed=False, reason="liquidity filter not satisfied")
            estimated_slippage = decision.metadata.get("estimated_slippage_pct", 0.0)
            if isinstance(estimated_slippage, (int, float)) and estimated_slippage > self.config.slippage_tolerance:
                return RiskCheckResult(allowed=False, reason="estimated slippage exceeds tolerance")
        return RiskCheckResult(allowed=True, reason="risk checks passed")
