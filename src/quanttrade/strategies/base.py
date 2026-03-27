from __future__ import annotations

from abc import ABC, abstractmethod

from quanttrade.config.models import StrategyConfig
from quanttrade.core.types import AccountState, MarketBar, PositionState, StrategyDecision


class Strategy(ABC):
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    @abstractmethod
    def generate_signal(
        self,
        market_bar: MarketBar,
        position_state: PositionState,
        account_state: AccountState,
    ) -> StrategyDecision:
        raise NotImplementedError
