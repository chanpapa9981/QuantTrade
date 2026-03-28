"""历史 dashboard HTML 导出测试。"""

import csv
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from quanttrade.app import QuantTradeApp


class HistoryHtmlTestCase(unittest.TestCase):
    def test_export_history_html_writes_expected_sections(self) -> None:
        """确认历史页包含执行视图、生命周期、筛选器、分享态和异常聚焦相关区域。"""
        base_dir = Path("var/test-artifacts/history-html")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "history-html-test.duckdb"
        config_path = base_dir / "settings.yaml"
        output_path = base_dir / "history.html"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 4, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(30):
                current = start + timedelta(days=offset)
                price += 1.0
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.7, 2),
                        "high": round(price + 0.5, 2),
                        "low": round(price - 1.0, 2),
                        "close": round(price, 2),
                        "volume": 2_300_000 + offset * 1000,
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
        app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        result = app.export_history_html(runs_limit=10, events_limit=10, output_path=str(output_path))

        self.assertEqual(result["output_path"], str(output_path))
        self.assertTrue(output_path.exists())
        html = output_path.read_text(encoding="utf-8")
        self.assertIn("Run History Dashboard", html)
        self.assertIn("Execution Attempts", html)
        self.assertIn("Request Chains", html)
        self.assertIn("Retried Requests", html)
        self.assertIn("Anomalous Requests", html)
        self.assertIn("Critical Requests", html)
        self.assertIn("Cooldown Active", html)
        self.assertIn("Retry Scheduled", html)
        self.assertIn("Top Failure Class", html)
        self.assertIn("Notifications", html)
        self.assertIn("Critical Alerts", html)
        self.assertIn("Queued Alerts", html)
        self.assertIn("Execution Requests", html)
        self.assertIn("Request Anomalies", html)
        self.assertIn("Recent Executions", html)
        self.assertIn("Execution Request Detail", html)
        self.assertIn("Execution Detail", html)
        self.assertIn("Request ID", html)
        self.assertIn("Health", html)
        self.assertIn("Anomaly Score", html)
        self.assertIn("Cooldown Until", html)
        self.assertIn("Failure Mix", html)
        self.assertIn("Retry", html)
        self.assertIn("Failure Class", html)
        self.assertIn("Protection Starts", html)
        self.assertIn("Execution Blocked", html)
        self.assertIn("Lifecycle Filled", html)
        self.assertIn("Recent Runs", html)
        self.assertIn("Order Lifecycles", html)
        self.assertIn("Broker", html)
        self.assertIn("Lifecycle Detail", html)
        self.assertIn("execution-table", html)
        self.assertIn("request-table", html)
        self.assertIn("request-detail-table", html)
        self.assertIn("execution-status-filter", html)
        self.assertIn("blocked", html)
        self.assertIn("lifecycle-filter", html)
        self.assertIn("run-filter", html)
        self.assertIn("side-filter", html)
        self.assertIn("broker-filter", html)
        self.assertIn("focus-filter", html)
        self.assertIn("selected-context", html)
        self.assertIn("Deep Link", html)
        self.assertIn("Copy Link", html)
        self.assertIn("clear-context", html)
        self.assertIn("Anomalies", html)
        self.assertIn("navigator.clipboard", html)
        self.assertIn("window.location.hash", html)
        self.assertIn("Recent Orders", html)
        self.assertIn("Recent Notifications", html)
        self.assertIn("Recent Audit Events", html)


if __name__ == "__main__":
    unittest.main()
