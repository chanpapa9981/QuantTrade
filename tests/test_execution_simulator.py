import unittest
from datetime import datetime, timezone

from quanttrade.config.models import ExecutionConfig
from quanttrade.core.types import AccountState, PositionState, SignalType, StrategyDecision
from quanttrade.execution.simulator import SimulatedExecutionEngine


class SimulatedExecutionEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SimulatedExecutionEngine(
            ExecutionConfig(
                commission_per_order=1.0,
                commission_per_share=0.005,
                min_commission=1.0,
                simulated_slippage_bps=5.0,
                max_fill_ratio_per_bar=0.01,
            )
        )
        self.timestamp = datetime.now(timezone.utc)

    def test_partial_entry_generates_partial_fill_and_cancellation(self) -> None:
        result = self.engine.execute(
            timestamp=self.timestamp,
            symbol="AAPL",
            market_price=100.0,
            market_volume=1_000.0,
            account_state=AccountState(equity=100_000.0, cash=100_000.0),
            position_state=PositionState(symbol="AAPL"),
            decision=StrategyDecision(
                signal=SignalType.LONG_ENTRY,
                reason="breakout",
                quantity=25,
                stop_loss=95.0,
            ),
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.position_state.quantity, 10)
        self.assertEqual(len(result.fill_events), 1)
        self.assertEqual(len(result.order_events), 2)
        self.assertEqual(result.order_events[0].status.value, "partially_filled")
        self.assertEqual(result.order_events[0].filled_quantity, 10)
        self.assertEqual(result.order_events[0].remaining_quantity, 15)
        self.assertEqual(result.order_events[1].status.value, "cancelled")
        self.assertEqual(result.order_events[1].quantity, 15)

    def test_duplicate_entry_is_rejected_when_position_already_open(self) -> None:
        result = self.engine.execute(
            timestamp=self.timestamp,
            symbol="AAPL",
            market_price=100.0,
            market_volume=10_000.0,
            account_state=AccountState(equity=100_000.0, cash=95_000.0, open_positions=1),
            position_state=PositionState(symbol="AAPL", quantity=10, entry_price=99.5, stop_loss=95.0, market_price=100.0),
            decision=StrategyDecision(
                signal=SignalType.LONG_ENTRY,
                reason="duplicate breakout",
                quantity=10,
                stop_loss=95.0,
            ),
        )

        self.assertFalse(result.accepted)
        self.assertEqual(len(result.order_events), 1)
        self.assertEqual(result.order_events[0].status.value, "rejected")
        self.assertIn("duplicate", result.order_events[0].reason)

    def test_partial_exit_reduces_position_and_cancels_remainder(self) -> None:
        result = self.engine.execute(
            timestamp=self.timestamp,
            symbol="AAPL",
            market_price=105.0,
            market_volume=500.0,
            account_state=AccountState(equity=100_500.0, cash=99_000.0, open_positions=1),
            position_state=PositionState(symbol="AAPL", quantity=12, entry_price=100.0, stop_loss=98.0, market_price=105.0),
            decision=StrategyDecision(
                signal=SignalType.LONG_EXIT,
                reason="exit signal",
            ),
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.position_state.quantity, 7)
        self.assertEqual(len(result.fill_events), 1)
        self.assertEqual(result.fill_events[0].quantity, 5)
        self.assertEqual(result.order_events[0].status.value, "partially_filled")
        self.assertEqual(result.order_events[0].filled_quantity, 5)
        self.assertEqual(result.order_events[0].remaining_quantity, 7)
        self.assertEqual(result.order_events[1].status.value, "cancelled")
        self.assertEqual(result.order_events[1].quantity, 7)


if __name__ == "__main__":
    unittest.main()
