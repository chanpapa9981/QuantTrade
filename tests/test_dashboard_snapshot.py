"""Dashboard 数据快照测试。"""

import csv
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from quanttrade.app import QuantTradeApp


class DashboardSnapshotTestCase(unittest.TestCase):
    def test_dashboard_snapshot_contains_summary_and_charts(self) -> None:
        """确认 dashboard 数据载荷包含前端展示所需的关键结构。"""
        base_dir = Path("var/test-artifacts/dashboard")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "dashboard-test.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 2, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(30):
                current = start + timedelta(days=offset)
                price += 1.1
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.7, 2),
                        "high": round(price + 0.5, 2),
                        "low": round(price - 1.0, 2),
                        "close": round(price, 2),
                        "volume": 2_100_000 + offset * 1000,
                    }
                )

        config_path.write_text(
            "\n".join(
                [
                    "strategy:",
                    "  symbol: AAPL",
                    "  entry_donchian_n: 5",
                    "  exit_donchian_m: 3",
                    "  atr_smooth_period: 5",
                    "  risk_coefficient_k: 2.0",
                    "  adx_trend_filter: 5.0",
                    "data:",
                    f"  duckdb_path: {db_path}",
                    "  backend: duckdb",
                ]
            ),
            encoding="utf-8",
        )

        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")
        payload = app.dashboard_snapshot(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)

        self.assertIn("summary_cards", payload)
        self.assertIn("charts", payload)
        self.assertIn("equity_curve", payload["charts"])
        self.assertIn("drawdown_curve", payload["charts"])
        self.assertIn("order_summary", payload)
        self.assertIn("audit_timeline", payload)
        self.assertIn("open_orders", payload["order_summary"])
        self.assertIn("replaced_orders", payload["order_summary"])
        self.assertIn("partial_orders", payload["order_summary"])
        self.assertIn("cancelled_orders", payload["order_summary"])
        self.assertGreaterEqual(len(payload["summary_cards"]), 4)


if __name__ == "__main__":
    unittest.main()
