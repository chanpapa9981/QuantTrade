"""数据导入与回测集成测试。"""

import csv
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from quanttrade.app import QuantTradeApp
from quanttrade.core.exceptions import NonRetryableExecutionError, RetryableExecutionError
from quanttrade.data.repository import BacktestRunRepository
from quanttrade.data.schema import create_schema
from quanttrade.data.storage import LockUnavailableError, connect_database, database_lock, execution_lock


class DataImportAndBacktestTestCase(unittest.TestCase):
    def _write_config(
        self,
        config_path: Path,
        db_path: Path,
        max_fill_ratio_per_bar: float = 0.05,
        open_order_timeout_bars: int = 2,
        max_retry_attempts: int = 2,
        retry_backoff_seconds: float = 0.0,
        retry_backoff_strategy: str = "linear",
        retry_backoff_multiplier: float = 2.0,
        max_retry_backoff_seconds: float = 30.0,
        protection_mode_failure_threshold: int = 2,
        protection_mode_cooldown_seconds: int = 0,
        skip_run_on_protection_mode: bool = True,
        notification_enabled: bool = False,
        notification_provider: str = "telegram",
        notification_min_level: str = "warning",
        notification_outbox_path: str = "var/notifications/test-outbox.jsonl",
        notification_delivery_log_path: str = "var/notifications/test-delivery-log.jsonl",
        notification_max_delivery_attempts: int = 3,
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
                    f"  retry_backoff_seconds: {retry_backoff_seconds}",
                    f"  retry_backoff_strategy: {retry_backoff_strategy}",
                    f"  retry_backoff_multiplier: {retry_backoff_multiplier}",
                    f"  max_retry_backoff_seconds: {max_retry_backoff_seconds}",
                    f"  protection_mode_failure_threshold: {protection_mode_failure_threshold}",
                    f"  protection_mode_cooldown_seconds: {protection_mode_cooldown_seconds}",
                    f"  skip_run_on_protection_mode: {'true' if skip_run_on_protection_mode else 'false'}",
                    "notification:",
                    f"  provider: {notification_provider}",
                    f"  enabled: {'true' if notification_enabled else 'false'}",
                    f"  min_level: {notification_min_level}",
                    f"  outbox_path: {notification_outbox_path}",
                    f"  delivery_log_path: {notification_delivery_log_path}",
                    f"  max_delivery_attempts: {notification_max_delivery_attempts}",
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
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

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
        recent_request_chains = app.recent_execution_requests(limit=5)
        recent_executions = app.recent_backtest_executions(limit=5)
        request_detail = app.execution_request_detail(request_id=persist_result["request_id"])
        execution_detail = app.execution_detail(execution_id=persist_result["execution_id"])
        protection_status = app.protection_status(symbol="AAPL", timeframe="1d")
        run_detail = app.backtest_run_detail(run_id=persist_result["run_id"])
        recent_orders = app.recent_order_events(limit=5)
        order_detail = app.order_detail(order_id=run_detail["detail"]["orders"][0]["order_id"])
        recent_audit = app.recent_audit_events(limit=5)
        recent_notifications = app.recent_notification_events(limit=5)
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
        self.assertEqual(persist_result["execution"]["retry_decision"], "completed")
        self.assertGreaterEqual(len(recent_runs["runs"]), 1)
        self.assertGreaterEqual(len(recent_request_chains["requests"]), 1)
        self.assertGreaterEqual(len(recent_executions["executions"]), 1)
        self.assertEqual(recent_request_chains["requests"][0]["request_id"], persist_result["request_id"])
        self.assertFalse(recent_request_chains["requests"][0]["retried"])
        self.assertEqual(recent_request_chains["requests"][0]["health_label"], "healthy")
        self.assertEqual(recent_request_chains["requests"][0]["anomaly_score"], 0)
        self.assertIsNotNone(request_detail["detail"])
        self.assertEqual(request_detail["detail"]["request"]["request_id"], persist_result["request_id"])
        self.assertEqual(request_detail["detail"]["request"]["attempt_count"], 1)
        self.assertEqual(request_detail["detail"]["request"]["health_label"], "healthy")
        self.assertEqual(request_detail["detail"]["request"]["failure_classes"], [])
        self.assertEqual(request_detail["detail"]["attempts"][0]["execution_id"], persist_result["execution_id"])
        self.assertEqual(recent_executions["executions"][0]["status"], "completed")
        self.assertIsNotNone(execution_detail["detail"])
        self.assertEqual(execution_detail["detail"]["execution"]["execution_id"], persist_result["execution_id"])
        self.assertEqual(execution_detail["detail"]["execution"]["attempt_number"], 1)
        self.assertFalse(execution_detail["detail"]["execution"]["protection_mode"])
        self.assertEqual(execution_detail["detail"]["execution"]["retry_decision"], "completed")
        self.assertFalse(protection_status["protection"]["active"])
        self.assertEqual(protection_status["protection"]["consecutive_failures"], 0)
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
        self.assertEqual(len(recent_notifications["notifications"]), 0)
        self.assertIn("history_summary", history_payload)
        self.assertIn("recent_executions", history_payload)
        self.assertIn("execution_requests", history_payload)
        self.assertIn("execution_request_details", history_payload)
        self.assertGreaterEqual(len(history_payload["recent_executions"]), 1)
        self.assertGreaterEqual(len(history_payload["execution_requests"]), 1)
        self.assertIn("total_executions", history_payload["history_summary"])
        self.assertIn("total_execution_requests", history_payload["history_summary"])
        self.assertIn("retried_execution_requests", history_payload["history_summary"])
        self.assertIn("anomalous_execution_requests", history_payload["history_summary"])
        self.assertIn("critical_execution_requests", history_payload["history_summary"])
        self.assertIn("retry_scheduled_executions", history_payload["history_summary"])
        self.assertIn("protection_mode_executions", history_payload["history_summary"])
        self.assertIn("top_request_failure_class", history_payload["history_summary"])
        self.assertIn("total_notifications", history_payload["history_summary"])
        self.assertIn("critical_notifications", history_payload["history_summary"])
        self.assertIn("queued_notifications", history_payload["history_summary"])
        self.assertIn("pending_notifications", history_payload["history_summary"])
        self.assertIn("dispatched_notifications", history_payload["history_summary"])
        self.assertIn("failed_notifications", history_payload["history_summary"])
        self.assertIn("request_anomalies", history_payload)
        self.assertIn("recent_notifications", history_payload)

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
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

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

        self._write_config(
            config_path,
            db_path,
            max_retry_attempts=2,
            retry_backoff_seconds=1.5,
            retry_backoff_strategy="exponential",
            retry_backoff_multiplier=3.0,
            max_retry_backoff_seconds=10.0,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")

        call_count = {"value": 0}

        def flaky_run_series(engine_self, bars, initial_equity):
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise RetryableExecutionError("transient failure from retry test")
            return original_engine_run_series(engine_self, bars=bars, initial_equity=initial_equity)

        from quanttrade.app import BacktestEngine

        original_engine_run_series = BacktestEngine.run_series
        with patch("quanttrade.app.BacktestEngine.run_series", new=flaky_run_series):
            with patch("quanttrade.app.time.sleep") as mocked_sleep:
                persist_result = app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)

        recent_executions = app.recent_backtest_executions(limit=5)
        recent_request_chains = app.recent_execution_requests(limit=5)
        request_detail = app.execution_request_detail(request_id=persist_result["request_id"])
        recent_notifications = app.recent_notification_events(limit=5)

        self.assertEqual(persist_result["status"], "completed")
        self.assertIn("request_id", persist_result)
        self.assertEqual(persist_result["attempts_used"], 2)
        self.assertEqual(persist_result["retry_count"], 1)
        self.assertEqual(call_count["value"], 2)
        mocked_sleep.assert_called_once_with(1.5)
        self.assertTrue(recent_request_chains["requests"][0]["retried"])
        self.assertEqual(recent_request_chains["requests"][0]["attempt_count"], 2)
        self.assertEqual(recent_request_chains["requests"][0]["health_label"], "watch")
        self.assertEqual(recent_request_chains["requests"][0]["retry_scheduled_count"], 1)
        self.assertEqual(recent_request_chains["requests"][0]["dominant_failure_class"], "RetryableExecutionError")
        self.assertGreater(recent_request_chains["requests"][0]["anomaly_score"], 0)
        self.assertEqual(request_detail["detail"]["request"]["attempt_count"], 2)
        self.assertEqual(request_detail["detail"]["request"]["health_label"], "watch")
        self.assertEqual(
            request_detail["detail"]["request"]["failure_classes"][0]["failure_class"],
            "RetryableExecutionError",
        )
        self.assertEqual(len(request_detail["detail"]["attempts"]), 2)
        self.assertEqual(recent_executions["executions"][0]["status"], "completed")
        self.assertEqual(recent_executions["executions"][0]["attempt_number"], 2)
        self.assertEqual(recent_executions["executions"][0]["retry_decision"], "completed")
        self.assertEqual(recent_executions["executions"][1]["status"], "failed")
        self.assertTrue(recent_executions["executions"][1]["retryable"])
        self.assertEqual(recent_executions["executions"][1]["retry_decision"], "retry_scheduled")
        self.assertEqual(recent_executions["executions"][1]["failure_class"], "RetryableExecutionError")
        self.assertEqual(recent_executions["executions"][0]["request_id"], persist_result["request_id"])
        self.assertEqual(recent_executions["executions"][1]["request_id"], persist_result["request_id"])
        self.assertIn("transient failure", recent_executions["executions"][1]["error_message"])
        self.assertGreaterEqual(len(recent_notifications["notifications"]), 2)
        self.assertEqual(recent_notifications["notifications"][0]["category"], "execution_recovered")
        self.assertEqual(recent_notifications["notifications"][0]["delivery_status"], "queued")
        self.assertEqual(recent_notifications["notifications"][1]["category"], "execution_retry_scheduled")
        self.assertTrue(outbox_path.exists())
        self.assertGreaterEqual(len(outbox_path.read_text(encoding="utf-8").splitlines()), 2)

    def test_persist_backtest_run_stops_immediately_on_non_retryable_failure(self) -> None:
        """验证明确声明为不可重试的错误不会被运行控制器反复重试。"""
        base_dir = Path("var/test-artifacts/execution-no-retry")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "no-retry-test.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 7, 20, tzinfo=timezone.utc)
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

        self._write_config(
            config_path,
            db_path,
            max_retry_attempts=3,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")

        from quanttrade.app import BacktestEngine

        call_count = {"value": 0}
        original_engine_run_series = BacktestEngine.run_series

        def fatal_run_series(engine_self, bars, initial_equity):
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise NonRetryableExecutionError("fatal validation failure from retry policy test")
            return original_engine_run_series(engine_self, bars=bars, initial_equity=initial_equity)

        with patch("quanttrade.app.BacktestEngine.run_series", new=fatal_run_series):
            with self.assertRaises(NonRetryableExecutionError):
                app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)

        recent_executions = app.recent_backtest_executions(limit=5)
        recent_request_chains = app.recent_execution_requests(limit=5)
        request_detail = app.execution_request_detail(request_id=recent_executions["executions"][0]["request_id"])
        recent_notifications = app.recent_notification_events(limit=5)

        self.assertEqual(call_count["value"], 1)
        self.assertEqual(recent_executions["executions"][0]["status"], "failed")
        self.assertFalse(recent_executions["executions"][0]["retryable"])
        self.assertEqual(recent_executions["executions"][0]["retry_decision"], "final_failure")
        self.assertEqual(recent_executions["executions"][0]["failure_class"], "NonRetryableExecutionError")
        self.assertEqual(recent_request_chains["requests"][0]["health_label"], "critical")
        self.assertEqual(recent_request_chains["requests"][0]["final_failure_count"], 1)
        self.assertEqual(recent_request_chains["requests"][0]["non_retryable_failure_count"], 1)
        self.assertEqual(recent_request_chains["requests"][0]["dominant_failure_class"], "NonRetryableExecutionError")
        self.assertEqual(request_detail["detail"]["request"]["health_label"], "critical")
        self.assertEqual(recent_notifications["notifications"][0]["category"], "execution_final_failure")
        self.assertEqual(recent_notifications["notifications"][0]["delivery_status"], "queued")
        self.assertTrue(outbox_path.exists())

    def test_notification_worker_dispatches_queued_events_to_local_adapter_log(self) -> None:
        """验证通知 worker 会把 queued 事件推进为 dispatched，并留下 adapter 处理痕迹。"""
        base_dir = Path("var/test-artifacts/notification-dispatch")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-dispatch.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        delivery_log_path = base_dir / "delivery-log.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()
        if delivery_log_path.exists():
            delivery_log_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_delivery_log_path=str(delivery_log_path),
            notification_max_delivery_attempts=3,
        )
        app = QuantTradeApp(str(config_path))

        notification = app._record_notification(
            severity="warning",
            category="execution_retry_scheduled",
            title="Retry scheduled",
            message="worker dispatch test",
            symbol="AAPL",
            timeframe="1d",
            execution_id="exec-1",
            request_id="req-1",
        )
        before_delivery = app.recent_notification_events(limit=5)
        delivery_result = app.deliver_notifications(limit=5)
        after_delivery = app.recent_notification_events(limit=5)
        history_payload = app.dashboard_history(runs_limit=5, events_limit=5)

        self.assertEqual(notification["delivery_status"], "queued")
        self.assertEqual(before_delivery["notifications"][0]["delivery_status"], "queued")
        self.assertEqual(delivery_result["processed"], 1)
        self.assertEqual(delivery_result["dispatched"], 1)
        self.assertEqual(delivery_result["failed_retryable"], 0)
        self.assertEqual(delivery_result["failed_final"], 0)
        self.assertEqual(delivery_result["remaining_pending"], 0)
        self.assertEqual(after_delivery["notifications"][0]["delivery_status"], "dispatched")
        self.assertEqual(after_delivery["notifications"][0]["delivery_attempts"], 1)
        self.assertTrue(after_delivery["notifications"][0]["delivered_at"])
        self.assertEqual(after_delivery["notifications"][0]["last_error"], "")
        self.assertEqual(history_payload["history_summary"]["dispatched_notifications"], 1)
        self.assertEqual(history_payload["history_summary"]["pending_notifications"], 0)
        self.assertTrue(outbox_path.exists())
        self.assertTrue(delivery_log_path.exists())
        delivered_payload = json.loads(delivery_log_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(delivered_payload["category"], "execution_retry_scheduled")
        self.assertEqual(delivered_payload["adapter_provider"], "telegram")

    def test_notification_worker_marks_retryable_and_final_delivery_failures(self) -> None:
        """验证通知 worker 在 adapter 失败时会区分“还能再试”和“最终放弃”两种状态。"""
        base_dir = Path("var/test-artifacts/notification-delivery-failure")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-delivery-failure.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        delivery_log_path = base_dir / "delivery-log.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()
        if delivery_log_path.exists():
            delivery_log_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_provider="failing_stub",
            notification_outbox_path=str(outbox_path),
            notification_delivery_log_path=str(delivery_log_path),
            notification_max_delivery_attempts=2,
        )
        app = QuantTradeApp(str(config_path))
        app._record_notification(
            severity="critical",
            category="execution_final_failure",
            title="Final failure",
            message="worker failure test",
            symbol="AAPL",
            timeframe="1d",
            execution_id="exec-2",
            request_id="req-2",
        )

        first_delivery = app.deliver_notifications(limit=5)
        after_first = app.recent_notification_events(limit=5)
        first_history = app.dashboard_history(runs_limit=5, events_limit=5)
        second_delivery = app.deliver_notifications(limit=5)
        after_second = app.recent_notification_events(limit=5)
        second_history = app.dashboard_history(runs_limit=5, events_limit=5)

        self.assertEqual(first_delivery["processed"], 1)
        self.assertEqual(first_delivery["failed_retryable"], 1)
        self.assertEqual(first_delivery["failed_final"], 0)
        self.assertEqual(after_first["notifications"][0]["delivery_status"], "delivery_failed_retryable")
        self.assertEqual(after_first["notifications"][0]["delivery_attempts"], 1)
        self.assertIn("simulated notification adapter failure", after_first["notifications"][0]["last_error"])
        self.assertEqual(first_history["history_summary"]["pending_notifications"], 1)
        self.assertEqual(first_history["history_summary"]["failed_notifications"], 1)

        self.assertEqual(second_delivery["processed"], 1)
        self.assertEqual(second_delivery["failed_retryable"], 0)
        self.assertEqual(second_delivery["failed_final"], 1)
        self.assertEqual(second_delivery["remaining_pending"], 0)
        self.assertEqual(after_second["notifications"][0]["delivery_status"], "delivery_failed_final")
        self.assertEqual(after_second["notifications"][0]["delivery_attempts"], 2)
        self.assertIn("simulated notification adapter failure", after_second["notifications"][0]["last_error"])
        self.assertEqual(second_history["history_summary"]["pending_notifications"], 0)
        self.assertEqual(second_history["history_summary"]["failed_notifications"], 1)
        self.assertFalse(delivery_log_path.exists())

    def test_persist_backtest_run_blocks_when_protection_mode_requests_skip(self) -> None:
        """验证 protection mode 被触发且配置要求拦截时，本次调用会直接返回 blocked。"""
        base_dir = Path("var/test-artifacts/execution-blocked")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "blocked-test.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            max_retry_attempts=3,
            protection_mode_failure_threshold=2,
            skip_run_on_protection_mode=True,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
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
        recent_request_chains = app.recent_execution_requests(limit=5)
        request_detail = app.execution_request_detail(request_id=blocked_result["request_id"])
        recent_notifications = app.recent_notification_events(limit=5)

        self.assertEqual(blocked_result["status"], "blocked")
        self.assertIsNone(blocked_result["run_id"])
        self.assertIn("request_id", blocked_result)
        self.assertEqual(blocked_result["attempts_used"], 1)
        self.assertEqual(blocked_result["retry_count"], 0)
        self.assertTrue(blocked_result["execution"]["protection_mode"])
        self.assertEqual(blocked_result["execution"]["retry_decision"], "blocked_protection_mode")
        self.assertEqual(recent_request_chains["requests"][0]["final_status"], "blocked")
        self.assertTrue(recent_request_chains["requests"][0]["blocked"])
        self.assertEqual(recent_request_chains["requests"][0]["health_label"], "critical")
        self.assertEqual(recent_request_chains["requests"][0]["dominant_failure_class"], "ProtectionMode")
        self.assertFalse(recent_request_chains["requests"][0]["cooldown_active"])
        self.assertTrue(request_detail["detail"]["request"]["blocked"])
        self.assertEqual(request_detail["detail"]["request"]["health_label"], "critical")
        self.assertEqual(recent_executions["executions"][0]["request_id"], blocked_result["request_id"])
        self.assertEqual(recent_executions["executions"][0]["status"], "blocked")
        self.assertTrue(recent_executions["executions"][0]["protection_mode"])
        self.assertEqual(recent_executions["executions"][0]["failure_class"], "ProtectionMode")
        self.assertEqual(recent_notifications["notifications"][0]["category"], "execution_blocked")
        self.assertEqual(recent_notifications["notifications"][0]["delivery_status"], "queued")
        self.assertTrue(outbox_path.exists())

    def test_retry_backoff_uses_exponential_strategy_and_cap(self) -> None:
        """验证退避计算支持指数增长，并会被最大等待时间封顶。"""
        base_dir = Path("var/test-artifacts/retry-backoff")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "retry-backoff.duckdb"
        config_path = base_dir / "settings.yaml"

        self._write_config(
            config_path,
            db_path,
            retry_backoff_seconds=1.5,
            retry_backoff_strategy="exponential",
            retry_backoff_multiplier=3.0,
            max_retry_backoff_seconds=10.0,
        )
        app = QuantTradeApp(str(config_path))

        self.assertEqual(app._compute_retry_backoff_seconds(1), 1.5)
        self.assertEqual(app._compute_retry_backoff_seconds(2), 4.5)
        self.assertEqual(app._compute_retry_backoff_seconds(3), 10.0)

    def test_execution_enters_cooldown_based_protection_mode(self) -> None:
        """验证连续失败达到阈值且仍在冷却窗口内时，新 execution 会带上 cooldown 信息。"""
        base_dir = Path("var/test-artifacts/protection-cooldown-active")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "cooldown-active.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        self._write_config(
            config_path,
            db_path,
            protection_mode_failure_threshold=2,
            protection_mode_cooldown_seconds=3600,
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
                protection_mode_cooldown_seconds=3600,
            )
            repository.mark_execution_failed(first, "first cooldown failure")
            second = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
                protection_mode_failure_threshold=2,
                protection_mode_cooldown_seconds=3600,
            )
            repository.mark_execution_failed(second, "second cooldown failure")
            third = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
                protection_mode_failure_threshold=2,
                protection_mode_cooldown_seconds=3600,
            )
            detail = repository.fetch_execution_detail(third)

        self.assertIsNotNone(detail)
        self.assertTrue(detail["execution"]["protection_mode"])
        self.assertIn("cooldown active until", detail["execution"]["protection_reason"])
        self.assertTrue(detail["execution"]["protection_cooldown_until"])
        protection_status = app.protection_status(symbol="AAPL", timeframe="1d")
        self.assertTrue(protection_status["protection"]["active"])
        self.assertTrue(protection_status["protection"]["protection_cooldown_until"])

    def test_persist_backtest_run_resumes_after_protection_cooldown_expires(self) -> None:
        """验证冷却窗口过期后，即使之前连续失败，系统也会允许新的回测重新启动。"""
        base_dir = Path("var/test-artifacts/protection-cooldown-expired")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "cooldown-expired.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 8, 1, tzinfo=timezone.utc)
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

        self._write_config(
            config_path,
            db_path,
            protection_mode_failure_threshold=2,
            protection_mode_cooldown_seconds=300,
            skip_run_on_protection_mode=True,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")

        with database_lock(str(db_path)):
            create_schema(str(db_path))
            repository = BacktestRunRepository(str(db_path))
            first = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
                protection_mode_failure_threshold=2,
                protection_mode_cooldown_seconds=300,
            )
            repository.mark_execution_failed(first, "first old failure")
            second = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
                protection_mode_failure_threshold=2,
                protection_mode_cooldown_seconds=300,
            )
            repository.mark_execution_failed(second, "second old failure")

            connection = connect_database(str(db_path))
            try:
                old_time = datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()
                connection.execute(
                    """
                    UPDATE backtest_executions
                    SET requested_at = ?, started_at = ?, finished_at = ?
                    WHERE execution_id IN (?, ?)
                    """,
                    (old_time, old_time, old_time, first, second),
                )
            finally:
                connection.close()

        persist_result = app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        protection_status = app.protection_status(symbol="AAPL", timeframe="1d")
        recent_notifications = app.recent_notification_events(limit=5)

        self.assertEqual(persist_result["status"], "completed")
        self.assertFalse(persist_result["execution"]["protection_mode"])
        self.assertIn("protection cooldown expired", persist_result["execution"]["protection_reason"])
        self.assertTrue(persist_result["execution"]["protection_cooldown_until"])
        self.assertFalse(protection_status["protection"]["active"])
        self.assertEqual(protection_status["protection"]["latest_execution_status"], "completed")
        self.assertEqual(recent_notifications["notifications"][0]["category"], "protection_resumed")
        self.assertTrue(outbox_path.exists())

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
