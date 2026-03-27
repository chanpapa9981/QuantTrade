import unittest
from datetime import datetime, timezone

from quanttrade.config.models import StrategyConfig
from quanttrade.core.types import AccountState, MarketBar, PositionState, SignalType
from quanttrade.strategies.atr_dtf import AtrDynamicTrendFollowingStrategy


class AtrDtfStrategyTestCase(unittest.TestCase):
    def test_emits_long_entry_when_breakout_and_adx_match(self) -> None:
        strategy = AtrDynamicTrendFollowingStrategy(StrategyConfig(symbol="AAPL"))
        market_bar = MarketBar(
            timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=106.0,
            volume=2_500_000,
            atr=2.0,
            adx=30.0,
            donchian_high=103.0,
            donchian_low=96.0,
        )

        decision = strategy.generate_signal(
            market_bar=market_bar,
            position_state=PositionState(symbol="AAPL"),
            account_state=AccountState(equity=100_000.0, cash=100_000.0),
        )

        self.assertEqual(decision.signal, SignalType.LONG_ENTRY)
        self.assertGreater(decision.quantity, 0)
        self.assertIsNotNone(decision.stop_loss)


if __name__ == "__main__":
    unittest.main()
