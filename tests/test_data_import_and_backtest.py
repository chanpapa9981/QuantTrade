import csv
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from quanttrade.app import QuantTradeApp
from quanttrade.data.repository import BacktestRunRepository
from quanttrade.data.schema import create_schema
from quanttrade.data.storage import LockUnavailableError, database_lock, execution_lock


class DataImportAndBacktestTestCase(unittest.TestCase):
    def _write_config(
        self,
        config_path: Path,
        db_path: Path,
        max_fill_ratio_per_bar: float = 0.05,
        open_order_timeout_bars: int = 2,
    ) -> None:
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
                    "execution:",
                    f"  max_fill_ratio_per_bar: {max_fill_ratio_per_bar}",
                    f"  open_order_timeout_bars: {open_order_timeout_bars}",
                ]
            ),
            encoding="utf-8",
        )

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

        self._write_config(config_path, db_path)

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
        recent_executions = app.recent_backtest_executions(limit=5)
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
        self.assertIn("order_id", backtest_result["orders"][0])
        self.assertIn("filled_quantity", backtest_result["orders"][0])
        self.assertIn("remaining_quantity", backtest_result["orders"][0])
        self.assertTrue(report_path.exists())
        self.assertEqual(export_result["output_path"], str(report_path))
        self.assertIn("run_id", persist_result)
        self.assertIn("execution_id", persist_result)
        self.assertEqual(persist_result["recovered_executions"], 0)
        self.assertGreaterEqual(len(recent_runs["runs"]), 1)
        self.assertGreaterEqual(len(recent_executions["executions"]), 1)
        self.assertEqual(recent_executions["executions"][0]["status"], "completed")
        self.assertIsNotNone(run_detail["detail"])
        self.assertIn("account_snapshot", run_detail["detail"])
        self.assertGreaterEqual(len(recent_orders["orders"]), 1)
        self.assertGreaterEqual(len(recent_audit["audit_events"]), 1)
        self.assertIn("history_summary", history_payload)

    def test_persist_backtest_run_recovers_stale_execution(self) -> None:
        base_dir = Path("var/test-artifacts/execution-recovery")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "recovery-test.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 5, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(30):
                current = start + timedelta(days=offset)
                price += 1.1
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.7, 2),
                        "high": round(price + 0.6, 2),
                        "low": round(price - 1.0, 2),
                        "close": round(price, 2),
                        "volume": 2_000_000 + offset * 1000,
                    }
                )

        self._write_config(config_path, db_path)
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")

        with database_lock(str(db_path)):
            create_schema(str(db_path))
            repository = BacktestRunRepository(str(db_path))
            repository.create_execution(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)

        persist_result = app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        recent_executions = app.recent_backtest_executions(limit=5)

        self.assertEqual(persist_result["recovered_executions"], 1)
        self.assertEqual(recent_executions["executions"][0]["status"], "completed")
        self.assertEqual(recent_executions["executions"][1]["status"], "abandoned")

    def test_persist_backtest_run_rejects_duplicate_execution_lock(self) -> None:
        base_dir = Path("var/test-artifacts/execution-lock")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "lock-test.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 6, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(10):
                current = start + timedelta(days=offset)
                price += 1.0
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.6, 2),
                        "high": round(price + 0.4, 2),
                        "low": round(price - 0.9, 2),
                        "close": round(price, 2),
                        "volume": 2_100_000 + offset * 1000,
                    }
                )

        self._write_config(config_path, db_path)
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")

        with execution_lock(str(db_path), symbol="AAPL", timeframe="1d", blocking=False):
            with self.assertRaises(LockUnavailableError):
                app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)

    def test_backtest_keeps_orders_open_across_bars_and_times_out(self) -> None:
        base_dir = Path("var/test-artifacts/open-order-timeout")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "open-order-timeout.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 7, 1, tzinfo=timezone.utc)
            closes = [100.0, 101.0, 102.0, 103.0, 104.0, 108.0, 109.0, 110.0, 111.0]
            for offset, close in enumerate(closes):
                current = start + timedelta(days=offset)
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(close - 0.8, 2),
                        "high": round(close + 0.6, 2),
                        "low": round(close - 1.0, 2),
                        "close": round(close, 2),
                        "volume": 2_000_000,
                    }
                )

        self._write_config(
            config_path,
            db_path,
            max_fill_ratio_per_bar=0.0,
            open_order_timeout_bars=1,
        )

        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")
        backtest_result = app.backtest_symbol(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)

        statuses = [order["status"] for order in backtest_result["orders"]]
        self.assertIn("created", statuses)
        self.assertIn("open", statuses)
        self.assertIn("replaced", statuses)
        self.assertIn("cancelled", statuses)
        self.assertEqual(backtest_result["account"]["open_positions"], 0)


if __name__ == "__main__":
    unittest.main()
