"""风控引擎。

风控的原则是：只要某条规则不满足，就优先拦截，而不是让策略强行下单。
"""

from __future__ import annotations

from quanttrade.config.models import RiskConfig
from quanttrade.core.types import AccountState, MarketBar, StrategyDecision
from quanttrade.risk.base import RiskCheckResult


class RiskEngine:
    """负责在策略决策和执行之间做最后一道风险检查。"""

    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def validate(
        self,
        account_state: AccountState,
        decision: StrategyDecision,
        market_bar: MarketBar | None = None,
    ) -> RiskCheckResult:
        """校验当前决策是否符合账户和市场层面的风控要求。"""
        if decision.quantity < 0:
            return RiskCheckResult(allowed=False, reason="negative order quantity is invalid")
        # 先看账户级的硬性规则，这些规则通常比策略信号优先级更高。
        if account_state.daily_pnl_pct <= -self.config.max_daily_drawdown:
            return RiskCheckResult(allowed=False, reason="daily drawdown circuit breaker triggered")
        if account_state.exposure_pct >= self.config.global_max_exposure and decision.quantity > 0:
            return RiskCheckResult(allowed=False, reason="global exposure limit reached")
        if account_state.open_positions >= self.config.max_open_positions and decision.quantity > 0:
            return RiskCheckResult(allowed=False, reason="max open positions reached")
        if decision.quantity == 0 and decision.signal.value.endswith("entry"):
            return RiskCheckResult(allowed=False, reason="position size rounded down to zero")
        if market_bar and decision.signal.value.endswith("entry"):
            # 入场时额外看市场条件，避免在明显缺乏流动性的 bar 上下单。
            if market_bar.volume < self.config.liquidity_filter:
                return RiskCheckResult(allowed=False, reason="liquidity filter not satisfied")
            estimated_slippage = decision.metadata.get("estimated_slippage_pct", 0.0)
            if isinstance(estimated_slippage, (int, float)) and estimated_slippage > self.config.slippage_tolerance:
                return RiskCheckResult(allowed=False, reason="estimated slippage exceeds tolerance")
        return RiskCheckResult(allowed=True, reason="risk checks passed")
