import csv
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from quanttrade.app import QuantTradeApp


class DataImportAndBacktestTestCase(unittest.TestCase):
    def test_import_csv_and_run_backtest(self) -> None:
        base_dir = Path("var/test-artifacts/integration")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "quanttrade-test.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 1, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(30):
                current = start + timedelta(days=offset)
                price += 1.2
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.8, 2),
                        "high": round(price + 0.6, 2),
                        "low": round(price - 1.1, 2),
                        "close": round(price, 2),
                        "volume": 2_000_000 + offset * 1000,
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
                    "  backend: sqlite",
                ]
            ),
            encoding="utf-8",
        )

        app = QuantTradeApp(str(config_path))
        import_result = app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")
        backtest_result = app.backtest_symbol(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        report_path = base_dir / "backtest-report.json"
        export_result = app.export_backtest(
            symbol="AAPL",
            timeframe="1d",
            initial_equity=100_000.0,
            output_path=str(report_path),
        )
        persist_result = app.persist_backtest_run(
            symbol="AAPL",
            timeframe="1d",
            initial_equity=100_000.0,
        )
        recent_runs = app.recent_backtest_runs(limit=5)
        run_detail = app.backtest_run_detail(run_id=persist_result["run_id"])
        recent_orders = app.recent_order_events(limit=5)
        recent_audit = app.recent_audit_events(limit=5)
        history_payload = app.dashboard_history(runs_limit=5, events_limit=5)

        self.assertEqual(import_result["rows_inserted"], 30)
        self.assertEqual(backtest_result["bars_processed"], 30)
        self.assertGreaterEqual(backtest_result["metrics"]["total_trades"], 1)
        self.assertIn("ending_equity", backtest_result["metrics"])
        self.assertIn("profit_factor", backtest_result["metrics"])
        self.assertIn("avg_trade_pnl", backtest_result["metrics"])
        self.assertIn("sharpe_ratio", backtest_result["metrics"])
        self.assertIn("sortino_ratio", backtest_result["metrics"])
        self.assertIn("longest_underwater_bars", backtest_result["metrics"])
        self.assertIn("orders", backtest_result)
        self.assertIn("audit_log", backtest_result)
        self.assertIn("account", backtest_result)
        self.assertGreaterEqual(backtest_result["account"]["realized_pnl"], 0.0)
        self.assertIn("commission", backtest_result["trades"][0])
        self.assertIn("net_value", backtest_result["trades"][0])
        self.assertGreaterEqual(len(backtest_result["orders"]), 1)
        self.assertTrue(report_path.exists())
        self.assertEqual(export_result["output_path"], str(report_path))
        self.assertIn("run_id", persist_result)
        self.assertGreaterEqual(len(recent_runs["runs"]), 1)
        self.assertIsNotNone(run_detail["detail"])
        self.assertIn("account_snapshot", run_detail["detail"])
        self.assertGreaterEqual(len(recent_orders["orders"]), 1)
        self.assertGreaterEqual(len(recent_audit["audit_events"]), 1)
        self.assertIn("history_summary", history_payload)


if __name__ == "__main__":
    unittest.main()
