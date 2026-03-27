"""ATR 动态趋势跟踪策略。

策略逻辑非常直观：
1. 没持仓时，价格突破入场唐奇安高点且 ADX 足够强，则考虑做多；
2. 有持仓时，价格跌破止损或跌破离场唐奇安低点，则离场；
3. 其余情况维持不动。
"""

from __future__ import annotations

from quanttrade.config.models import StrategyConfig
from quanttrade.core.types import AccountState, MarketBar, PositionState, SignalType, StrategyDecision
from quanttrade.strategies.base import Strategy


class AtrDynamicTrendFollowingStrategy(Strategy):
    """项目当前默认使用的趋势跟踪策略。"""

    def __init__(self, config: StrategyConfig) -> None:
        super().__init__(config)

    def generate_signal(
        self,
        market_bar: MarketBar,
        position_state: PositionState,
        account_state: AccountState,
    ) -> StrategyDecision:
        """根据当前 bar 生成交易信号。"""
        stop_loss = self._calc_stop_loss(market_bar)

        if not position_state.is_open:
            # 没有持仓时，只检查“是否满足入场条件”。
            if market_bar.close > market_bar.donchian_high and market_bar.adx >= self.config.adx_trend_filter:
                quantity = self._calc_position_size(account_state, market_bar)
                return StrategyDecision(
                    signal=SignalType.LONG_ENTRY,
                    reason="price breaks Donchian high and ADX passes trend filter",
                    stop_loss=stop_loss,
                    quantity=quantity,
                    metadata={
                        "symbol": self.config.symbol,
                        "estimated_slippage_pct": 0.0005,
                    },
                )
            return StrategyDecision(signal=SignalType.HOLD, reason="entry conditions not met")

        # 有持仓时，先看最强的保护条件：止损是否已经被打穿。
        if position_state.stop_loss is not None and market_bar.close <= position_state.stop_loss:
            return StrategyDecision(
                signal=SignalType.LONG_EXIT,
                reason="close price breaches current stop loss",
            )

        # 其次看趋势是否已经明显走弱到触发离场通道。
        if market_bar.close < market_bar.donchian_low:
            return StrategyDecision(
                signal=SignalType.LONG_EXIT,
                reason="price falls below exit Donchian low",
            )

        return StrategyDecision(signal=SignalType.HOLD, reason="position remains valid", stop_loss=stop_loss)

    def _calc_stop_loss(self, market_bar: MarketBar) -> float:
        """按收盘价减去 `k * ATR` 计算动态止损位。"""
        return round(market_bar.close - self.config.risk_coefficient_k * market_bar.atr, 4)

    def _calc_position_size(self, account_state: AccountState, market_bar: MarketBar) -> int:
        """按“风险约束”和“权重约束”两套规则同时算仓位，最后取更保守的那个。"""
        atr_risk = max(self.config.risk_coefficient_k * market_bar.atr, 0.01)
        risk_quantity = int(account_state.equity * self.config.risk_pct / atr_risk)
        weight_quantity = int(account_state.equity * self.config.max_symbol_weight / market_bar.close)
        return max(min(risk_quantity, weight_quantity), 0)
