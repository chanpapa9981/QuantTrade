"""策略抽象基类。

所有策略都要实现统一接口，这样回测器和实盘执行层才不用关心“你到底是哪种策略”。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from quanttrade.config.models import StrategyConfig
from quanttrade.core.types import AccountState, MarketBar, PositionState, StrategyDecision


class Strategy(ABC):
    """所有策略实现都必须继承的基类。"""

    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    @abstractmethod
    def generate_signal(
        self,
        market_bar: MarketBar,
        position_state: PositionState,
        account_state: AccountState,
    ) -> StrategyDecision:
        """根据当前市场、持仓和账户状态生成策略决策。"""
        raise NotImplementedError
