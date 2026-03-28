"""数据导入与回测集成测试。"""

import csv
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

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
        max_retry_attempts: int = 2,
        protection_mode_failure_threshold: int = 2,
        skip_run_on_protection_mode: bool = True,
    ) -> None:
        """生成测试配置文件，方便不同测试复用同一套最小配置模板。"""
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
                    f"  max_retry_attempts: {max_retry_attempts}",
                    f"  protection_mode_failure_threshold: {protection_mode_failure_threshold}",
                    f"  skip_run_on_protection_mode: {'true' if skip_run_on_protection_mode else 'false'}",
                ]
            ),
            encoding="utf-8",
        )

    def test_import_csv_and_run_backtest(self) -> None:
        """验证导入、回测、导出、持久化、历史查询整条链路都能跑通。"""
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
        execution_detail = app.execution_detail(execution_id=persist_result["execution_id"])
        run_detail = app.backtest_run_detail(run_id=persist_result["run_id"])
        recent_orders = app.recent_order_events(limit=5)
        order_detail = app.order_detail(order_id=run_detail["detail"]["orders"][0]["order_id"])
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
        self.assertIn("broker_status", backtest_result["orders"][0])
        self.assertIn("status_detail", backtest_result["orders"][0])
        self.assertTrue(report_path.exists())
        self.assertEqual(export_result["output_path"], str(report_path))
        self.assertIn("run_id", persist_result)
        self.assertIn("request_id", persist_result)
        self.assertIn("execution_id", persist_result)
        self.assertEqual(persist_result["status"], "completed")
        self.assertEqual(persist_result["recovered_executions"], 0)
        self.assertEqual(persist_result["attempts_used"], 1)
        self.assertEqual(persist_result["retry_count"], 0)
        self.assertEqual(persist_result["execution"]["attempt_number"], 1)
        self.assertEqual(persist_result["execution"]["recovered_execution_count"], 0)
        self.assertEqual(persist_result["execution"]["consecutive_failures_before_start"], 0)
        self.assertFalse(persist_result["execution"]["protection_mode"])
        self.assertGreaterEqual(len(recent_runs["runs"]), 1)
        self.assertGreaterEqual(len(recent_executions["executions"]), 1)
        self.assertEqual(recent_executions["executions"][0]["status"], "completed")
        self.assertIsNotNone(execution_detail["detail"])
        self.assertEqual(execution_detail["detail"]["execution"]["execution_id"], persist_result["execution_id"])
        self.assertEqual(execution_detail["detail"]["execution"]["attempt_number"], 1)
        self.assertFalse(execution_detail["detail"]["execution"]["protection_mode"])
        self.assertEqual(execution_detail["detail"]["run"]["run_id"], persist_result["run_id"])
        self.assertIsNotNone(run_detail["detail"])
        self.assertIn("account_snapshot", run_detail["detail"])
        self.assertIn("order_lifecycles", run_detail["detail"])
        self.assertGreaterEqual(len(run_detail["detail"]["order_lifecycles"]), 1)
        self.assertIsNotNone(order_detail["detail"])
        self.assertIn("events", order_detail["detail"])
        self.assertIn("order", order_detail["detail"])
        self.assertEqual(order_detail["detail"]["order"]["order_id"], run_detail["detail"]["orders"][0]["order_id"])
        self.assertIn("latest_broker_status", order_detail["detail"]["order"])
        self.assertIn("status_detail", order_detail["detail"]["events"][0])
        self.assertGreaterEqual(len(recent_orders["orders"]), 1)
        self.assertIn("broker_status", recent_orders["orders"][0])
        self.assertGreaterEqual(len(recent_audit["audit_events"]), 1)
        self.assertIn("history_summary", history_payload)
        self.assertIn("recent_executions", history_payload)
        self.assertGreaterEqual(len(history_payload["recent_executions"]), 1)
        self.assertIn("total_executions", history_payload["history_summary"])
        self.assertIn("protection_mode_executions", history_payload["history_summary"])

    def test_persist_backtest_run_recovers_stale_execution(self) -> None:
        """验证中断后残留的 running execution 能被自动恢复标记。"""
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
            repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
            )

        persist_result = app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        recent_executions = app.recent_backtest_executions(limit=5)

        self.assertEqual(persist_result["recovered_executions"], 1)
        self.assertEqual(recent_executions["executions"][0]["status"], "completed")
        self.assertEqual(recent_executions["executions"][0]["attempt_number"], 2)
        self.assertEqual(recent_executions["executions"][0]["recovered_execution_count"], 1)
        self.assertEqual(recent_executions["executions"][1]["status"], "abandoned")

    def test_execution_enters_protection_mode_after_consecutive_failures(self) -> None:
        """验证连续失败达到阈值后，新执行记录会带上保护模式标记。"""
        base_dir = Path("var/test-artifacts/execution-protection")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "protection-test.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        self._write_config(config_path, db_path)
        app = QuantTradeApp(str(config_path))

        with database_lock(str(db_path)):
            create_schema(str(db_path))
            repository = BacktestRunRepository(str(db_path))
            first = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
            )
            repository.mark_execution_failed(first, "first failure")
            second = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
            )
            repository.mark_execution_failed(second, "second failure")
            third = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
            )
            repository.mark_execution_failed(third, "third failure")

        recent_executions = app.recent_backtest_executions(limit=5)

        self.assertEqual(recent_executions["executions"][0]["attempt_number"], 3)
        self.assertEqual(recent_executions["executions"][0]["consecutive_failures_before_start"], 2)
        self.assertTrue(recent_executions["executions"][0]["protection_mode"])
        self.assertIn("protection mode", recent_executions["executions"][0]["protection_reason"])

    def test_persist_backtest_run_retries_after_transient_failure(self) -> None:
        """验证同一次调用里遇到瞬时失败后，会自动创建新 execution 重试并最终成功。"""
        base_dir = Path("var/test-artifacts/execution-retry")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "retry-test.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 7, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(30):
                current = start + timedelta(days=offset)
                price += 1.0
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.7, 2),
                        "high": round(price + 0.6, 2),
                        "low": round(price - 1.0, 2),
                        "close": round(price, 2),
                        "volume": 2_200_000 + offset * 1000,
                    }
                )

        self._write_config(config_path, db_path, max_retry_attempts=2)
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")

        call_count = {"value": 0}

        def flaky_run_series(engine_self, bars, initial_equity):
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise RuntimeError("transient failure from retry test")
            return original_engine_run_series(engine_self, bars=bars, initial_equity=initial_equity)

        from quanttrade.app import BacktestEngine

        original_engine_run_series = BacktestEngine.run_series
        with patch("quanttrade.app.BacktestEngine.run_series", new=flaky_run_series):
            persist_result = app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)

        recent_executions = app.recent_backtest_executions(limit=5)

        self.assertEqual(persist_result["status"], "completed")
        self.assertIn("request_id", persist_result)
        self.assertEqual(persist_result["attempts_used"], 2)
        self.assertEqual(persist_result["retry_count"], 1)
        self.assertEqual(call_count["value"], 2)
        self.assertEqual(recent_executions["executions"][0]["status"], "completed")
        self.assertEqual(recent_executions["executions"][0]["attempt_number"], 2)
        self.assertEqual(recent_executions["executions"][1]["status"], "failed")
        self.assertEqual(recent_executions["executions"][0]["request_id"], persist_result["request_id"])
        self.assertEqual(recent_executions["executions"][1]["request_id"], persist_result["request_id"])
        self.assertIn("transient failure", recent_executions["executions"][1]["error_message"])

    def test_persist_backtest_run_blocks_when_protection_mode_requests_skip(self) -> None:
        """验证 protection mode 被触发且配置要求拦截时，本次调用会直接返回 blocked。"""
        base_dir = Path("var/test-artifacts/execution-blocked")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "blocked-test.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        self._write_config(
            config_path,
            db_path,
            max_retry_attempts=3,
            protection_mode_failure_threshold=2,
            skip_run_on_protection_mode=True,
        )
        app = QuantTradeApp(str(config_path))

        with database_lock(str(db_path)):
            create_schema(str(db_path))
            repository = BacktestRunRepository(str(db_path))
            first = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
                protection_mode_failure_threshold=2,
            )
            repository.mark_execution_failed(first, "first failure")
            second = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
                protection_mode_failure_threshold=2,
            )
            repository.mark_execution_failed(second, "second failure")

        blocked_result = app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        recent_executions = app.recent_backtest_executions(limit=5)

        self.assertEqual(blocked_result["status"], "blocked")
        self.assertIsNone(blocked_result["run_id"])
        self.assertIn("request_id", blocked_result)
        self.assertEqual(blocked_result["attempts_used"], 1)
        self.assertEqual(blocked_result["retry_count"], 0)
        self.assertTrue(blocked_result["execution"]["protection_mode"])
        self.assertEqual(recent_executions["executions"][0]["request_id"], blocked_result["request_id"])
        self.assertEqual(recent_executions["executions"][0]["status"], "blocked")
        self.assertTrue(recent_executions["executions"][0]["protection_mode"])

    def test_persist_backtest_run_rejects_duplicate_execution_lock(self) -> None:
        """验证同标的同周期重复执行时，会被运行锁直接拦住。"""
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
        """验证挂单可以跨 bar 存活，并在超时后自动取消。"""
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
        self.assertIn("broker_status", backtest_result["orders"][0])
        self.assertEqual(backtest_result["account"]["open_positions"], 0)


if __name__ == "__main__":
    unittest.main()
