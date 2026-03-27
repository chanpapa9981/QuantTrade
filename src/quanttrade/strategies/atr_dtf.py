from __future__ import annotations

from quanttrade.config.models import StrategyConfig
from quanttrade.core.types import AccountState, MarketBar, PositionState, SignalType, StrategyDecision
from quanttrade.strategies.base import Strategy


class AtrDynamicTrendFollowingStrategy(Strategy):
    def __init__(self, config: StrategyConfig) -> None:
        super().__init__(config)

    def generate_signal(
        self,
        market_bar: MarketBar,
        position_state: PositionState,
        account_state: AccountState,
    ) -> StrategyDecision:
        stop_loss = self._calc_stop_loss(market_bar)

        if not position_state.is_open:
            if market_bar.close > market_bar.donchian_high and market_bar.adx >= self.config.adx_trend_filter:
                quantity = self._calc_position_size(account_state, market_bar)
                return StrategyDecision(
                    signal=SignalType.LONG_ENTRY,
                    reason="price breaks Donchian high and ADX passes trend filter",
                    stop_loss=stop_loss,
                    quantity=quantity,
                    metadata={"symbol": self.config.symbol},
                )
            return StrategyDecision(signal=SignalType.HOLD, reason="entry conditions not met")

        if position_state.stop_loss is not None and market_bar.close <= position_state.stop_loss:
            return StrategyDecision(
                signal=SignalType.LONG_EXIT,
                reason="close price breaches current stop loss",
            )

        if market_bar.close < market_bar.donchian_low:
            return StrategyDecision(
                signal=SignalType.LONG_EXIT,
                reason="price falls below exit Donchian low",
            )

        return StrategyDecision(signal=SignalType.HOLD, reason="position remains valid", stop_loss=stop_loss)

    def _calc_stop_loss(self, market_bar: MarketBar) -> float:
        return round(market_bar.close - self.config.risk_coefficient_k * market_bar.atr, 4)

    def _calc_position_size(self, account_state: AccountState, market_bar: MarketBar) -> int:
        atr_risk = max(self.config.risk_coefficient_k * market_bar.atr, 0.01)
        risk_quantity = int(account_state.equity * self.config.risk_pct / atr_risk)
        weight_quantity = int(account_state.equity * self.config.max_symbol_weight / market_bar.close)
        return max(min(risk_quantity, weight_quantity), 0)
