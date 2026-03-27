"""模拟执行器测试。"""

import unittest
from datetime import datetime, timezone

from quanttrade.config.models import ExecutionConfig
from quanttrade.core.types import AccountState, PositionState, SignalType, StrategyDecision
from quanttrade.execution.simulator import SimulatedExecutionEngine


class SimulatedExecutionEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        """准备一套固定执行配置，避免不同测试互相影响。"""
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
        """当流动性不足时，入场订单应只成交一部分，并保留剩余数量。"""
        result = self.engine.execute(
            timestamp=self.timestamp,
            order_id="order-entry-1",
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
        self.assertEqual(len(result.order_events), 1)
        self.assertEqual(result.order_events[0].status.value, "partially_filled")
        self.assertEqual(result.order_events[0].broker_status, "partially_filled")
        self.assertEqual(result.order_events[0].status_detail, "entry_partial_fill_waiting")
        self.assertEqual(result.order_events[0].filled_quantity, 10)
        self.assertEqual(result.order_events[0].remaining_quantity, 15)

    def test_duplicate_entry_is_rejected_when_position_already_open(self) -> None:
        """已有持仓时再次发同向入场单，应被执行层拒绝。"""
        result = self.engine.execute(
            timestamp=self.timestamp,
            order_id="order-entry-2",
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
        self.assertEqual(result.order_events[0].broker_status, "rejected")
        self.assertEqual(result.order_events[0].status_detail, "duplicate_position_guard")
        self.assertIn("duplicate", result.order_events[0].reason)

    def test_partial_exit_reduces_position_and_cancels_remainder(self) -> None:
        """退出时如果流动性不足，应先部分卖出并保留剩余仓位。"""
        result = self.engine.execute(
            timestamp=self.timestamp,
            order_id="order-exit-1",
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
        self.assertEqual(result.order_events[0].broker_status, "partially_filled")
        self.assertEqual(result.order_events[0].status_detail, "exit_partial_fill_waiting")
        self.assertEqual(result.order_events[0].filled_quantity, 5)
        self.assertEqual(result.order_events[0].remaining_quantity, 7)

    def test_zero_liquidity_keeps_order_open(self) -> None:
        """完全没有流动性时，订单应保持 open，而不是伪造成交。"""
        result = self.engine.execute(
            timestamp=self.timestamp,
            order_id="order-entry-open",
            symbol="AAPL",
            market_price=100.0,
            market_volume=0.0,
            account_state=AccountState(equity=100_000.0, cash=100_000.0),
            position_state=PositionState(symbol="AAPL"),
            decision=StrategyDecision(
                signal=SignalType.LONG_ENTRY,
                reason="breakout",
                quantity=12,
                stop_loss=95.0,
            ),
        )

        self.assertTrue(result.accepted)
        self.assertEqual(len(result.fill_events), 0)
        self.assertEqual(len(result.order_events), 1)
        self.assertEqual(result.order_events[0].status.value, "open")
        self.assertEqual(result.order_events[0].broker_status, "working")
        self.assertEqual(result.order_events[0].status_detail, "awaiting_entry_liquidity")
        self.assertEqual(result.order_events[0].remaining_quantity, 12)


if __name__ == "__main__":
    unittest.main()
