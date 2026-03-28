"""数据导入与回测集成测试。"""

import csv
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from quanttrade.app import QuantTradeApp
from quanttrade.backtest.engine import BacktestEngine
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
        notification_delivery_retry_backoff_seconds: float = 0.0,
        notification_delivery_retry_backoff_strategy: str = "linear",
        notification_delivery_retry_backoff_multiplier: float = 2.0,
        notification_max_delivery_retry_backoff_seconds: float = 300.0,
        notification_silence_window_seconds: int = 0,
        notification_escalation_window_seconds: int = 0,
        notification_escalation_min_severity: str = "critical",
        notification_assignment_sla_seconds: int = 0,
        notification_assignment_sla_warning_seconds: int = 0,
        notification_assignment_sla_error_seconds: int = 0,
        notification_assignment_sla_critical_seconds: int = 0,
        notification_reopen_resets_acknowledgement: bool = True,
        execution_retryable_failure_classes: str = "RetryableExecutionError",
        execution_non_retryable_failure_classes: str = "NonRetryableExecutionError",
        execution_protection_trigger_failure_classes: str = "",
        execution_reconcile_on_write: bool = True,
        live_enabled: bool = False,
        live_runner_id: str = "local-default",
        live_poll_interval_seconds: float = 0.0,
        live_max_cycles_per_run: int = 1,
        broker_enabled: bool = False,
        broker_provider: str = "local_file",
        broker_account_snapshot_path: str = "var/broker/account.json",
        broker_positions_snapshot_path: str = "var/broker/positions.json",
        broker_orders_snapshot_path: str = "var/broker/orders.json",
        broker_max_snapshot_age_seconds: int = 0,
        broker_equity_drift_threshold: float = 0.0,
        broker_cash_drift_threshold: float = 0.0,
        broker_position_count_drift_threshold: int = 0,
        broker_open_order_drift_threshold: int = 0,
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
                    f"  retryable_failure_classes: {execution_retryable_failure_classes}",
                    f"  non_retryable_failure_classes: {execution_non_retryable_failure_classes}",
                    f"  protection_trigger_failure_classes: {execution_protection_trigger_failure_classes}",
                    f"  reconcile_on_write: {'true' if execution_reconcile_on_write else 'false'}",
                    "live:",
                    f"  enabled: {'true' if live_enabled else 'false'}",
                    f"  runner_id: {live_runner_id}",
                    f"  poll_interval_seconds: {live_poll_interval_seconds}",
                    f"  max_cycles_per_run: {live_max_cycles_per_run}",
                    "broker:",
                    f"  enabled: {'true' if broker_enabled else 'false'}",
                    f"  provider: {broker_provider}",
                    f"  account_snapshot_path: {broker_account_snapshot_path}",
                    f"  positions_snapshot_path: {broker_positions_snapshot_path}",
                    f"  orders_snapshot_path: {broker_orders_snapshot_path}",
                    f"  max_snapshot_age_seconds: {broker_max_snapshot_age_seconds}",
                    f"  equity_drift_threshold: {broker_equity_drift_threshold}",
                    f"  cash_drift_threshold: {broker_cash_drift_threshold}",
                    f"  position_count_drift_threshold: {broker_position_count_drift_threshold}",
                    f"  open_order_drift_threshold: {broker_open_order_drift_threshold}",
                    "notification:",
                    f"  provider: {notification_provider}",
                    f"  enabled: {'true' if notification_enabled else 'false'}",
                    f"  min_level: {notification_min_level}",
                    f"  outbox_path: {notification_outbox_path}",
                    f"  delivery_log_path: {notification_delivery_log_path}",
                    f"  max_delivery_attempts: {notification_max_delivery_attempts}",
                    f"  delivery_retry_backoff_seconds: {notification_delivery_retry_backoff_seconds}",
                    f"  delivery_retry_backoff_strategy: {notification_delivery_retry_backoff_strategy}",
                    f"  delivery_retry_backoff_multiplier: {notification_delivery_retry_backoff_multiplier}",
                    f"  max_delivery_retry_backoff_seconds: {notification_max_delivery_retry_backoff_seconds}",
                    f"  silence_window_seconds: {notification_silence_window_seconds}",
                    f"  escalation_window_seconds: {notification_escalation_window_seconds}",
                    f"  escalation_min_severity: {notification_escalation_min_severity}",
                    f"  assignment_sla_seconds: {notification_assignment_sla_seconds}",
                    f"  assignment_sla_warning_seconds: {notification_assignment_sla_warning_seconds}",
                    f"  assignment_sla_error_seconds: {notification_assignment_sla_error_seconds}",
                    f"  assignment_sla_critical_seconds: {notification_assignment_sla_critical_seconds}",
                    f"  reopen_resets_acknowledgement: {'true' if notification_reopen_resets_acknowledgement else 'false'}",
                ]
            ),
            encoding="utf-8",
        )

    def _write_broker_snapshots(self, base_dir: Path) -> tuple[Path, Path, Path]:
        """生成本地 broker fixture，模拟真实券商返回的账户/持仓/订单快照。"""
        broker_dir = base_dir / "broker"
        broker_dir.mkdir(parents=True, exist_ok=True)
        account_path = broker_dir / "account.json"
        positions_path = broker_dir / "positions.json"
        orders_path = broker_dir / "orders.json"
        account_path.write_text(
            json.dumps(
                {
                    "account_id": "paper-account",
                    "currency": "USD",
                    "equity": 125000.5,
                    "cash": 48250.25,
                    "buying_power": 240000.0,
                    "source_updated_at": datetime(2026, 3, 28, tzinfo=timezone.utc).isoformat(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        positions_path.write_text(
            json.dumps(
                [
                    {
                        "symbol": "AAPL",
                        "quantity": 120,
                        "market_price": 192.5,
                        "average_cost": 180.0,
                        "market_value": 23100.0,
                        "unrealized_pnl": 1500.0,
                        "source_updated_at": datetime(2026, 3, 28, tzinfo=timezone.utc).isoformat(),
                    },
                    {
                        "symbol": "MSFT",
                        "quantity": 50,
                        "market_price": 410.0,
                        "average_cost": 401.0,
                        "market_value": 20500.0,
                        "unrealized_pnl": 450.0,
                        "source_updated_at": datetime(2026, 3, 28, tzinfo=timezone.utc).isoformat(),
                    },
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        orders_path.write_text(
            json.dumps(
                [
                    {
                        "broker_order_id": "broker-order-1",
                        "symbol": "AAPL",
                        "side": "BUY",
                        "status": "working",
                        "quantity": 120,
                        "filled_quantity": 60,
                        "limit_price": 191.8,
                        "stop_price": 0.0,
                        "submitted_at": datetime(2026, 3, 28, 1, tzinfo=timezone.utc).isoformat(),
                        "source_updated_at": datetime(2026, 3, 28, 1, 30, tzinfo=timezone.utc).isoformat(),
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return account_path, positions_path, orders_path

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
        notification_summary = app.notification_summary(limit=5)
        notification_owner_summary = app.notification_owner_summary(limit=5)
        notification_sla_summary = app.notification_sla_summary(limit=5)
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
        self.assertIn("summary", notification_summary)
        self.assertIn("summary", notification_owner_summary)
        self.assertIn("summary", notification_sla_summary)
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
        self.assertIn("scheduled_retry_notifications", history_payload["history_summary"])
        self.assertIn("silenced_notification_groups", history_payload["history_summary"])
        self.assertIn("suppressed_duplicates", history_payload["history_summary"])
        self.assertIn("acknowledged_notifications", history_payload["history_summary"])
        self.assertIn("unacknowledged_notifications", history_payload["history_summary"])
        self.assertIn("resolved_notifications", history_payload["history_summary"])
        self.assertIn("reopened_notifications", history_payload["history_summary"])
        self.assertIn("active_notifications", history_payload["history_summary"])
        self.assertIn("assigned_notifications", history_payload["history_summary"])
        self.assertIn("unassigned_notifications", history_payload["history_summary"])
        self.assertIn("escalated_notifications", history_payload["history_summary"])
        self.assertIn("escalated_unassigned_notifications", history_payload["history_summary"])
        self.assertIn("sla_breached_notifications", history_payload["history_summary"])
        self.assertIn("controller_health_issues", history_payload["history_summary"])
        self.assertIn("stale_execution_candidates", history_payload["history_summary"])
        self.assertIn("runtime_reconcile_candidates", history_payload["history_summary"])
        self.assertIn("request_anomalies", history_payload)
        self.assertIn("recent_live_cycles", history_payload)
        self.assertIn("recent_notifications", history_payload)
        self.assertIn("notification_owner_summary", history_payload)
        self.assertIn("notification_inbox", history_payload)
        self.assertIn("notification_sla_summary", history_payload)
        self.assertIn("controller_health", history_payload)
        self.assertIn("total_live_cycles", history_payload["history_summary"])
        self.assertIn("completed_live_cycles", history_payload["history_summary"])
        self.assertIn("skipped_live_cycles", history_payload["history_summary"])
        self.assertIn("live_runners", history_payload["history_summary"])
        self.assertIn("idle_live_runners", history_payload["history_summary"])
        self.assertIn("stalled_live_runners", history_payload["history_summary"])
        self.assertIn("live_runner_summary", history_payload)

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

    def test_live_run_cycle_completes_and_links_persisted_run(self) -> None:
        """验证 live cycle 在检测到新数据时会落成一次完整 persisted run。"""
        base_dir = Path("var/test-artifacts/live-cycle-complete")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "live-cycle-complete.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 6, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(30):
                current = start + timedelta(days=offset)
                price += 1.0
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.6, 2),
                        "high": round(price + 0.7, 2),
                        "low": round(price - 1.0, 2),
                        "close": round(price, 2),
                        "volume": 2_200_000 + offset * 1000,
                    }
                )

        self._write_config(
            config_path,
            db_path,
            live_enabled=True,
            live_runner_id="paper-runner",
            live_poll_interval_seconds=0.0,
            live_max_cycles_per_run=1,
        )
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")

        cycle_result = app.live_run_cycle(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        recent_cycles = app.recent_live_cycles(limit=5)["live_cycles"]

        self.assertEqual(cycle_result["status"], "completed")
        self.assertEqual(cycle_result["cycle"]["status"], "completed")
        self.assertEqual(cycle_result["cycle"]["runner_id"], "paper-runner")
        self.assertEqual(cycle_result["cycle"]["processed_bar_count"], 30)
        self.assertTrue(cycle_result["cycle"]["latest_bar_at"])
        self.assertTrue(cycle_result["cycle"]["request_id"])
        self.assertTrue(cycle_result["cycle"]["execution_id"])
        self.assertTrue(cycle_result["cycle"]["run_id"])
        self.assertEqual(recent_cycles[0]["cycle_id"], cycle_result["cycle"]["cycle_id"])
        self.assertEqual(recent_cycles[0]["status"], "completed")

    def test_live_run_cycle_skips_when_market_watermark_does_not_advance(self) -> None:
        """验证 live runner 在没有新 bar 时会显式记一次 skipped cycle。"""
        base_dir = Path("var/test-artifacts/live-cycle-skip")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "live-cycle-skip.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 6, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(30):
                current = start + timedelta(days=offset)
                price += 0.8
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.5, 2),
                        "high": round(price + 0.5, 2),
                        "low": round(price - 0.9, 2),
                        "close": round(price, 2),
                        "volume": 2_100_000 + offset * 1000,
                    }
                )

        self._write_config(
            config_path,
            db_path,
            live_enabled=True,
            live_runner_id="paper-runner",
            live_poll_interval_seconds=0.0,
            live_max_cycles_per_run=1,
        )
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")

        first = app.live_run_cycle(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        second = app.live_run_cycle(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        recent_cycles = app.recent_live_cycles(limit=5)["live_cycles"]
        runner_summary = app.live_runner_status(limit=10)["summary"]

        self.assertEqual(first["status"], "completed")
        self.assertEqual(second["status"], "skipped")
        self.assertEqual(second["cycle"]["skip_reason"], "no_new_data")
        self.assertEqual(recent_cycles[0]["status"], "skipped")
        self.assertEqual(recent_cycles[1]["status"], "completed")
        self.assertEqual(runner_summary[0]["runner_id"], "paper-runner")
        self.assertEqual(runner_summary[0]["latest_status"], "skipped")
        self.assertEqual(runner_summary[0]["idle_streak"], 1)

    def test_live_run_cycle_records_blocked_status_when_controller_is_protected(self) -> None:
        """验证 live cycle 会把控制器 protection block 显式落成 blocked 周期。"""
        base_dir = Path("var/test-artifacts/live-cycle-blocked")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "live-cycle-blocked.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 6, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(30):
                current = start + timedelta(days=offset)
                price += 1.0
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.6, 2),
                        "high": round(price + 0.5, 2),
                        "low": round(price - 1.0, 2),
                        "close": round(price, 2),
                        "volume": 2_000_000 + offset * 1000,
                    }
                )

        self._write_config(
            config_path,
            db_path,
            live_enabled=True,
            live_runner_id="paper-runner",
            live_poll_interval_seconds=0.0,
            live_max_cycles_per_run=1,
            protection_mode_failure_threshold=1,
            skip_run_on_protection_mode=True,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")

        with database_lock(str(db_path)):
            create_schema(str(db_path))
            repository = BacktestRunRepository(str(db_path))
            first_execution = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
            )
            repository.mark_execution_failed(first_execution, "trigger live protection")

        cycle_result = app.live_run_cycle(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        recent_cycles = app.recent_live_cycles(limit=5)["live_cycles"]

        self.assertEqual(cycle_result["status"], "blocked")
        self.assertEqual(cycle_result["cycle"]["status"], "blocked")
        self.assertEqual(cycle_result["cycle"]["skip_reason"], "protection_mode")
        self.assertTrue(cycle_result["cycle"]["protection_mode"])
        self.assertEqual(recent_cycles[0]["status"], "blocked")

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
        self.assertEqual(after_delivery["notifications"][0]["next_delivery_attempt_at"], "")
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
            notification_delivery_retry_backoff_seconds=60.0,
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
        blocked_second_delivery = app.deliver_notifications(limit=5)

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET next_delivery_attempt_at = ?
                WHERE event_id = ?
                """,
                ("2024-01-01T00:00:00+00:00", after_first["notifications"][0]["event_id"]),
            )
        finally:
            connection.close()

        second_delivery = app.deliver_notifications(limit=5)
        after_second = app.recent_notification_events(limit=5)
        second_history = app.dashboard_history(runs_limit=5, events_limit=5)

        self.assertEqual(first_delivery["processed"], 1)
        self.assertEqual(first_delivery["failed_retryable"], 1)
        self.assertEqual(first_delivery["failed_final"], 0)
        self.assertEqual(after_first["notifications"][0]["delivery_status"], "delivery_failed_retryable")
        self.assertEqual(after_first["notifications"][0]["delivery_attempts"], 1)
        self.assertIn("simulated notification adapter failure", after_first["notifications"][0]["last_error"])
        self.assertTrue(after_first["notifications"][0]["next_delivery_attempt_at"])
        self.assertEqual(first_history["history_summary"]["pending_notifications"], 1)
        self.assertEqual(first_history["history_summary"]["failed_notifications"], 1)
        self.assertEqual(first_history["history_summary"]["scheduled_retry_notifications"], 1)

        self.assertEqual(blocked_second_delivery["processed"], 0)
        self.assertEqual(blocked_second_delivery["remaining_pending"], 0)

        self.assertEqual(second_delivery["processed"], 1)
        self.assertEqual(second_delivery["failed_retryable"], 0)
        self.assertEqual(second_delivery["failed_final"], 1)
        self.assertEqual(second_delivery["remaining_pending"], 0)
        self.assertEqual(after_second["notifications"][0]["delivery_status"], "delivery_failed_final")
        self.assertEqual(after_second["notifications"][0]["delivery_attempts"], 2)
        self.assertIn("simulated notification adapter failure", after_second["notifications"][0]["last_error"])
        self.assertEqual(after_second["notifications"][0]["next_delivery_attempt_at"], "")
        self.assertEqual(second_history["history_summary"]["pending_notifications"], 0)
        self.assertEqual(second_history["history_summary"]["failed_notifications"], 1)
        self.assertEqual(second_history["history_summary"]["scheduled_retry_notifications"], 0)
        self.assertFalse(delivery_log_path.exists())

    def test_notification_duplicates_are_silenced_within_window(self) -> None:
        """验证同类通知在静默窗口内不会重复生成新事件或重复写 outbox。"""
        base_dir = Path("var/test-artifacts/notification-silence")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-silence.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_silence_window_seconds=300,
        )
        app = QuantTradeApp(str(config_path))

        first = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="first blocked event",
            symbol="AAPL",
            timeframe="1d",
        )
        second = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="second blocked event should be silenced",
            symbol="AAPL",
            timeframe="1d",
        )
        recent_notifications = app.recent_notification_events(limit=5)
        history_payload = app.dashboard_history(runs_limit=5, events_limit=5)
        summary_rows = app.notification_summary(limit=5)

        self.assertEqual(first["delivery_status"], "queued")
        self.assertEqual(second["delivery_status"], "silenced_duplicate")
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(len(recent_notifications["notifications"]), 1)
        self.assertEqual(recent_notifications["notifications"][0]["suppressed_duplicate_count"], 1)
        self.assertTrue(recent_notifications["notifications"][0]["silenced_until"])
        self.assertTrue(recent_notifications["notifications"][0]["last_suppressed_at"])
        self.assertEqual(history_payload["history_summary"]["silenced_notification_groups"], 1)
        self.assertEqual(history_payload["history_summary"]["suppressed_duplicates"], 1)
        self.assertEqual(summary_rows["summary"][0]["category"], "execution_blocked")
        self.assertEqual(summary_rows["summary"][0]["suppressed_duplicates"], 1)
        self.assertEqual(len(outbox_path.read_text(encoding="utf-8").splitlines()), 1)

    def test_notification_duplicate_after_silence_window_creates_new_event(self) -> None:
        """验证静默窗口过期后，同类通知会重新生成新的通知事件。"""
        base_dir = Path("var/test-artifacts/notification-silence-expired")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-silence-expired.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_silence_window_seconds=300,
        )
        app = QuantTradeApp(str(config_path))

        first = app._record_notification(
            severity="critical",
            category="execution_final_failure",
            title="Backtest execution failed",
            message="first final failure",
            symbol="AAPL",
            timeframe="1d",
        )

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET silenced_until = ?
                WHERE event_id = ?
                """,
                ("2024-01-01T00:00:00+00:00", first["event_id"]),
            )
        finally:
            connection.close()

        second = app._record_notification(
            severity="critical",
            category="execution_final_failure",
            title="Backtest execution failed",
            message="second final failure after silence expired",
            symbol="AAPL",
            timeframe="1d",
        )
        recent_notifications = app.recent_notification_events(limit=5)

        self.assertEqual(first["delivery_status"], "queued")
        self.assertEqual(second["delivery_status"], "queued")
        self.assertNotEqual(first["event_id"], second["event_id"])
        self.assertEqual(len(recent_notifications["notifications"]), 2)
        self.assertEqual(len(outbox_path.read_text(encoding="utf-8").splitlines()), 2)

    def test_notification_ack_marks_event_reviewed(self) -> None:
        """验证通知可以被显式确认，方便把未处理告警和已查看告警区分开。"""
        base_dir = Path("var/test-artifacts/notification-ack")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-ack.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="warning",
            category="execution_retry_scheduled",
            title="Backtest retry scheduled",
            message="ack test",
            symbol="AAPL",
            timeframe="1d",
        )

        acked = app.acknowledge_notification(event_id=created["event_id"], note="checked by operator")
        recent_notifications = app.recent_notification_events(limit=5)
        history_payload = app.dashboard_history(runs_limit=5, events_limit=5)

        self.assertEqual(created["delivery_status"], "queued")
        self.assertIsNotNone(acked["notification"])
        self.assertEqual(acked["notification"]["event_id"], created["event_id"])
        self.assertTrue(acked["notification"]["acknowledged_at"])
        self.assertEqual(acked["notification"]["acknowledged_note"], "checked by operator")
        self.assertTrue(recent_notifications["notifications"][0]["acknowledged_at"])
        self.assertEqual(recent_notifications["notifications"][0]["acknowledged_note"], "checked by operator")
        self.assertEqual(history_payload["history_summary"]["acknowledged_notifications"], 1)
        self.assertEqual(history_payload["history_summary"]["unacknowledged_notifications"], 0)

    def test_notification_escalation_marks_stale_unacknowledged_alert(self) -> None:
        """验证高优先级且长期未确认的告警会被升级标记。"""
        base_dir = Path("var/test-artifacts/notification-escalation")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-escalation.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_escalation_window_seconds=60,
            notification_escalation_min_severity="error",
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="critical",
            category="execution_final_failure",
            title="Backtest execution failed",
            message="escalation test",
            symbol="AAPL",
            timeframe="1d",
        )

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET timestamp = ?
                WHERE event_id = ?
                """,
                ("2024-01-01T00:00:00+00:00", created["event_id"]),
            )
        finally:
            connection.close()

        result = app.escalate_notifications(limit=10)
        recent_notifications = app.recent_notification_events(limit=5)
        history_payload = app.dashboard_history(runs_limit=5, events_limit=5)

        self.assertEqual(result["escalated"], 1)
        self.assertEqual(recent_notifications["notifications"][0]["event_id"], created["event_id"])
        self.assertTrue(recent_notifications["notifications"][0]["escalated_at"])
        self.assertEqual(recent_notifications["notifications"][0]["escalation_level"], "stale_unacknowledged")
        self.assertIn("threshold=60s", recent_notifications["notifications"][0]["escalation_reason"])
        self.assertEqual(history_payload["history_summary"]["escalated_notifications"], 1)

    def test_notification_escalation_skips_acknowledged_alert(self) -> None:
        """验证已确认的告警不会再次进入升级流程。"""
        base_dir = Path("var/test-artifacts/notification-escalation-acked")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-escalation-acked.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_escalation_window_seconds=60,
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="acked escalation skip",
            symbol="AAPL",
            timeframe="1d",
        )
        app.acknowledge_notification(event_id=created["event_id"], note="already handled")

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET timestamp = ?
                WHERE event_id = ?
                """,
                ("2024-01-01T00:00:00+00:00", created["event_id"]),
            )
        finally:
            connection.close()

        result = app.escalate_notifications(limit=10)
        recent_notifications = app.recent_notification_events(limit=5)

        self.assertEqual(result["escalated"], 0)
        self.assertEqual(recent_notifications["notifications"][0]["event_id"], created["event_id"])
        self.assertEqual(recent_notifications["notifications"][0]["escalated_at"], "")

    def test_notification_assignment_marks_owner_and_note(self) -> None:
        """验证通知可以被分派给明确负责人。"""
        base_dir = Path("var/test-artifacts/notification-assignment")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-assignment.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="assignment test",
            symbol="AAPL",
            timeframe="1d",
        )

        assigned = app.assign_notification(
            event_id=created["event_id"],
            owner="ops.alice",
            note="follow up with broker mapping",
        )
        recent_notifications = app.recent_notification_events(limit=5)
        history_payload = app.dashboard_history(runs_limit=5, events_limit=5)

        self.assertIsNotNone(assigned["notification"])
        self.assertEqual(assigned["notification"]["event_id"], created["event_id"])
        self.assertEqual(assigned["notification"]["assigned_to"], "ops.alice")
        self.assertTrue(assigned["notification"]["assigned_at"])
        self.assertEqual(assigned["notification"]["assignment_note"], "follow up with broker mapping")
        self.assertEqual(recent_notifications["notifications"][0]["assigned_to"], "ops.alice")
        self.assertTrue(recent_notifications["notifications"][0]["assigned_at"])
        self.assertEqual(recent_notifications["notifications"][0]["assignment_note"], "follow up with broker mapping")
        self.assertEqual(history_payload["history_summary"]["assigned_notifications"], 1)
        self.assertEqual(history_payload["history_summary"]["unassigned_notifications"], 0)

    def test_notification_resolve_marks_event_completed(self) -> None:
        """验证通知可以被显式标记为已解决，方便把活跃待办和已完成事项区分开。"""
        base_dir = Path("var/test-artifacts/notification-resolve")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-resolve.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="warning",
            category="execution_retry_scheduled",
            title="Backtest retry scheduled",
            message="resolve test",
            symbol="AAPL",
            timeframe="1d",
        )

        resolved = app.resolve_notification(event_id=created["event_id"], note="manual mitigation finished")
        recent_notifications = app.recent_notification_events(limit=5)
        history_payload = app.dashboard_history(runs_limit=5, events_limit=5)

        self.assertIsNotNone(resolved["notification"])
        self.assertEqual(resolved["notification"]["event_id"], created["event_id"])
        self.assertTrue(resolved["notification"]["resolved_at"])
        self.assertEqual(resolved["notification"]["resolved_note"], "manual mitigation finished")
        self.assertTrue(recent_notifications["notifications"][0]["resolved_at"])
        self.assertEqual(recent_notifications["notifications"][0]["resolved_note"], "manual mitigation finished")
        self.assertEqual(history_payload["history_summary"]["resolved_notifications"], 1)
        self.assertEqual(history_payload["history_summary"]["active_notifications"], 0)

    def test_notification_reopen_restores_active_alert(self) -> None:
        """验证已解决通知可以被 reopen，重新回到活跃待办。"""
        base_dir = Path("var/test-artifacts/notification-reopen")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-reopen.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="reopen test",
            symbol="AAPL",
            timeframe="1d",
        )
        app.assign_notification(event_id=created["event_id"], owner="operator", note="take ownership")
        app.acknowledge_notification(event_id=created["event_id"], note="initial ack")
        app.resolve_notification(event_id=created["event_id"], note="first fix completed")

        reopened = app.reopen_notification(event_id=created["event_id"], note="issue recurred after resume")
        history_payload = app.dashboard_history(runs_limit=5, events_limit=5)
        inbox_rows = app.notification_inbox(limit=10)["inbox"]

        self.assertIsNotNone(reopened["notification"])
        self.assertEqual(reopened["notification"]["event_id"], created["event_id"])
        self.assertEqual(reopened["notification"]["resolved_at"], "")
        self.assertEqual(reopened["notification"]["resolved_note"], "")
        self.assertEqual(reopened["notification"]["acknowledged_at"], "")
        self.assertTrue(reopened["notification"]["reopened_at"])
        self.assertEqual(reopened["notification"]["reopened_note"], "issue recurred after resume")
        self.assertEqual(reopened["notification"]["reopen_count"], 1)
        self.assertEqual(history_payload["history_summary"]["reopened_notifications"], 1)
        self.assertEqual(history_payload["history_summary"]["active_notifications"], 1)
        self.assertEqual(inbox_rows[0]["event_id"], created["event_id"])
        self.assertTrue(inbox_rows[0]["reopened"])

    def test_notification_batch_reopen_restores_multiple_alerts(self) -> None:
        """验证批量 reopen 可以一次恢复多条已解决通知。"""
        base_dir = Path("var/test-artifacts/notification-batch-reopen")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-batch-reopen.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        first = app._record_notification(
            severity="warning",
            category="execution_retry_scheduled",
            title="Backtest retry scheduled",
            message="batch reopen first",
            symbol="AAPL",
            timeframe="1d",
        )
        second = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="batch reopen second",
            symbol="AAPL",
            timeframe="1d",
        )
        app.batch_resolve_notifications(
            event_ids=[first["event_id"], second["event_id"]],
            note="resolved before reopen",
        )

        reopened = app.batch_reopen_notifications(
            event_ids=[first["event_id"], second["event_id"]],
            note="reopened by batch",
        )
        recent_notifications = app.recent_notification_events(limit=5)["notifications"]

        self.assertEqual(reopened["processed"], 2)
        self.assertEqual(len(reopened["notifications"]), 2)
        self.assertEqual(recent_notifications[0]["resolved_at"], "")
        self.assertEqual(recent_notifications[1]["resolved_at"], "")
        self.assertEqual(recent_notifications[0]["reopen_count"], 1)
        self.assertEqual(recent_notifications[1]["reopen_count"], 1)

    def test_notification_batch_actions_update_multiple_events(self) -> None:
        """验证批量 assign / ack / resolve 能一次处理多条通知。"""
        base_dir = Path("var/test-artifacts/notification-batch")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-batch.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        first = app._record_notification(
            severity="warning",
            category="execution_retry_scheduled",
            title="Backtest retry scheduled",
            message="batch first",
            symbol="AAPL",
            timeframe="1d",
        )
        second = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="batch second",
            symbol="AAPL",
            timeframe="1d",
        )

        assign_result = app.batch_assign_notifications(
            event_ids=[first["event_id"], second["event_id"]],
            owner="operator",
            note="batch assignment",
        )
        ack_result = app.batch_acknowledge_notifications(
            event_ids=[first["event_id"], second["event_id"]],
            note="batch ack",
        )
        resolve_result = app.batch_resolve_notifications(
            event_ids=[first["event_id"], second["event_id"]],
            note="batch resolve",
        )
        recent_notifications = app.recent_notification_events(limit=5)["notifications"]

        self.assertEqual(assign_result["processed"], 2)
        self.assertEqual(ack_result["processed"], 2)
        self.assertEqual(resolve_result["processed"], 2)
        self.assertEqual(len(assign_result["notifications"]), 2)
        self.assertTrue(all(item["assigned_to"] == "operator" for item in assign_result["notifications"]))
        self.assertTrue(all(item["acknowledged_at"] for item in ack_result["notifications"]))
        self.assertTrue(all(item["resolved_at"] for item in resolve_result["notifications"]))
        self.assertTrue(all(item["resolved_note"] == "batch resolve" for item in recent_notifications[:2]))

    def test_notification_assignment_reduces_escalated_unowned_count(self) -> None:
        """验证升级告警在分派后不再被统计成无人接手。"""
        base_dir = Path("var/test-artifacts/notification-escalated-assigned")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-escalated-assigned.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_escalation_window_seconds=60,
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="critical",
            category="execution_final_failure",
            title="Backtest execution failed",
            message="escalated assignment test",
            symbol="AAPL",
            timeframe="1d",
        )

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET timestamp = ?
                WHERE event_id = ?
                """,
                ("2024-01-01T00:00:00+00:00", created["event_id"]),
            )
        finally:
            connection.close()

        app.escalate_notifications(limit=10)
        before_assign = app.dashboard_history(runs_limit=5, events_limit=5)
        app.assign_notification(event_id=created["event_id"], owner="ops.bob", note="take ownership after escalation")
        after_assign = app.dashboard_history(runs_limit=5, events_limit=5)

        self.assertEqual(before_assign["history_summary"]["escalated_unassigned_notifications"], 1)
        self.assertEqual(after_assign["history_summary"]["escalated_notifications"], 1)
        self.assertEqual(after_assign["history_summary"]["escalated_unassigned_notifications"], 0)

    def test_notification_owner_summary_groups_owner_load(self) -> None:
        """验证 owner 汇总可以看出谁手上还有多少未确认或已升级告警。"""
        base_dir = Path("var/test-artifacts/notification-owner-summary")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-owner-summary.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_escalation_window_seconds=60,
        )
        app = QuantTradeApp(str(config_path))
        first = app._record_notification(
            severity="critical",
            category="execution_final_failure",
            title="Backtest execution failed",
            message="owner summary critical",
            symbol="AAPL",
            timeframe="1d",
        )
        second = app._record_notification(
            severity="warning",
            category="execution_retry_scheduled",
            title="Backtest retry scheduled",
            message="owner summary warning",
            symbol="AAPL",
            timeframe="1d",
        )

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET timestamp = ?
                WHERE event_id = ?
                """,
                ("2024-01-01T00:00:00+00:00", first["event_id"]),
            )
        finally:
            connection.close()

        app.escalate_notifications(limit=10)
        app.assign_notification(event_id=first["event_id"], owner="ops.alice", note="critical queue")
        summary_rows = app.notification_owner_summary(limit=10)["summary"]

        owner_row = next(row for row in summary_rows if row["owner"] == "ops.alice")
        unassigned_row = next(row for row in summary_rows if row["owner"] == "(unassigned)")

        self.assertEqual(owner_row["event_count"], 1)
        self.assertEqual(owner_row["active_count"], 1)
        self.assertEqual(owner_row["resolved_count"], 0)
        self.assertEqual(owner_row["unacknowledged_count"], 1)
        self.assertEqual(owner_row["escalated_count"], 1)
        self.assertEqual(owner_row["open_high_priority_count"], 1)
        self.assertEqual(unassigned_row["event_count"], 1)
        self.assertEqual(unassigned_row["active_count"], 1)
        self.assertEqual(unassigned_row["resolved_count"], 0)
        self.assertEqual(unassigned_row["unacknowledged_count"], 1)
        self.assertEqual(unassigned_row["escalated_count"], 0)

    def test_notification_sla_summary_flags_overdue_assigned_alerts(self) -> None:
        """验证已分派但长期未确认的告警会进入 SLA 过期视图。"""
        base_dir = Path("var/test-artifacts/notification-sla")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-sla.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_assignment_sla_seconds=60,
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="sla test",
            symbol="AAPL",
            timeframe="1d",
        )
        app.assign_notification(event_id=created["event_id"], owner="operator", note="waiting for manual review")

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET assigned_at = ?
                WHERE event_id = ?
                """,
                ("2024-01-01T00:00:00+00:00", created["event_id"]),
            )
        finally:
            connection.close()

        sla_rows = app.notification_sla_summary(limit=10)["summary"]
        history_payload = app.dashboard_history(runs_limit=5, events_limit=10)

        self.assertEqual(len(sla_rows), 1)
        self.assertEqual(sla_rows[0]["event_id"], created["event_id"])
        self.assertEqual(sla_rows[0]["owner"], "operator")
        self.assertEqual(sla_rows[0]["sla_seconds"], 60)
        self.assertEqual(sla_rows[0]["sla_source"], "default")
        self.assertGreater(sla_rows[0]["breach_seconds"], 0)
        self.assertEqual(history_payload["history_summary"]["sla_breached_notifications"], 1)

    def test_notification_sla_summary_uses_severity_specific_override(self) -> None:
        """验证 critical / warning 可以使用不同的 SLA 阈值。"""
        base_dir = Path("var/test-artifacts/notification-sla-severity")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-sla-severity.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_assignment_sla_seconds=300,
            notification_assignment_sla_warning_seconds=600,
            notification_assignment_sla_critical_seconds=60,
        )
        app = QuantTradeApp(str(config_path))
        critical = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="critical sla",
            symbol="AAPL",
            timeframe="1d",
        )
        warning = app._record_notification(
            severity="warning",
            category="execution_retry_scheduled",
            title="Backtest retry scheduled",
            message="warning sla",
            symbol="AAPL",
            timeframe="1d",
        )
        app.batch_assign_notifications(
            event_ids=[critical["event_id"], warning["event_id"]],
            owner="operator",
            note="severity assignment",
        )

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET assigned_at = ?
                WHERE event_id IN (?, ?)
                """,
                ("2024-01-01T00:00:00+00:00", critical["event_id"], warning["event_id"]),
            )
        finally:
            connection.close()

        sla_rows = app.notification_sla_summary(limit=10)["summary"]

        self.assertEqual(len(sla_rows), 2)
        critical_row = next(item for item in sla_rows if item["event_id"] == critical["event_id"])
        warning_row = next(item for item in sla_rows if item["event_id"] == warning["event_id"])
        self.assertEqual(critical_row["sla_seconds"], 60)
        self.assertEqual(critical_row["sla_source"], "critical")
        self.assertEqual(warning_row["sla_seconds"], 600)
        self.assertEqual(warning_row["sla_source"], "warning")

    def test_notification_sla_summary_skips_acknowledged_alerts(self) -> None:
        """验证已确认的告警即使 assigned_at 很早，也不会继续算作 SLA 过期。"""
        base_dir = Path("var/test-artifacts/notification-sla-acked")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-sla-acked.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_assignment_sla_seconds=60,
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="critical",
            category="execution_final_failure",
            title="Backtest execution failed",
            message="sla acked skip",
            symbol="AAPL",
            timeframe="1d",
        )
        app.assign_notification(event_id=created["event_id"], owner="operator", note="already reviewing")
        app.acknowledge_notification(event_id=created["event_id"], note="handled")

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET assigned_at = ?
                WHERE event_id = ?
                """,
                ("2024-01-01T00:00:00+00:00", created["event_id"]),
            )
        finally:
            connection.close()

        sla_rows = app.notification_sla_summary(limit=10)["summary"]
        history_payload = app.dashboard_history(runs_limit=5, events_limit=10)

        self.assertEqual(sla_rows, [])
        self.assertEqual(history_payload["history_summary"]["sla_breached_notifications"], 0)

    def test_notification_sla_summary_skips_resolved_alerts(self) -> None:
        """验证已解决的告警不会继续停留在 SLA 过期列表里。"""
        base_dir = Path("var/test-artifacts/notification-sla-resolved")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-sla-resolved.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_assignment_sla_seconds=60,
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="sla resolved skip",
            symbol="AAPL",
            timeframe="1d",
        )
        app.assign_notification(event_id=created["event_id"], owner="operator", note="queued for fix")
        app.resolve_notification(event_id=created["event_id"], note="issue closed")

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET assigned_at = ?
                WHERE event_id = ?
                """,
                ("2024-01-01T00:00:00+00:00", created["event_id"]),
            )
        finally:
            connection.close()

        sla_rows = app.notification_sla_summary(limit=10)["summary"]
        history_payload = app.dashboard_history(runs_limit=5, events_limit=10)

        self.assertEqual(sla_rows, [])
        self.assertEqual(history_payload["history_summary"]["sla_breached_notifications"], 0)

    def test_runtime_reconcile_repairs_notification_timestamps_and_stale_executions(self) -> None:
        """验证控制器 reconcile 能修复缺失时间戳和残留 running execution。"""
        base_dir = Path("var/test-artifacts/runtime-reconcile")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "runtime-reconcile.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="critical",
            category="execution_final_failure",
            title="Backtest execution failed",
            message="reconcile notification",
            symbol="AAPL",
            timeframe="1d",
        )
        app.assign_notification(event_id=created["event_id"], owner="operator", note="reconcile owner")
        app.resolve_notification(event_id=created["event_id"], note="resolved before ack repair")

        with database_lock(str(db_path)):
            create_schema(str(db_path))
            repository = BacktestRunRepository(str(db_path))
            execution_id = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
            )

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET assigned_at = '',
                    acknowledged_at = '',
                    acknowledged_note = ''
                WHERE event_id = ?
                """,
                (created["event_id"],),
            )
        finally:
            connection.close()

        reconcile_result = app.reconcile_runtime_state()
        notifications = app.recent_notification_events(limit=5)["notifications"]
        executions = app.recent_backtest_executions(limit=5)["executions"]

        self.assertEqual(reconcile_result["repaired_assignment_timestamps"], 1)
        self.assertEqual(reconcile_result["repaired_resolution_acknowledgements"], 1)
        self.assertEqual(reconcile_result["recovered_stale_executions"], 1)
        self.assertTrue(notifications[0]["assigned_at"])
        self.assertTrue(notifications[0]["acknowledged_at"])
        self.assertEqual(executions[0]["execution_id"], execution_id)
        self.assertEqual(executions[0]["status"], "abandoned")

    def test_preview_runtime_reconcile_reports_candidates_without_writing(self) -> None:
        """验证 dry-run 预览只统计候选项，不直接改数据库。"""
        base_dir = Path("var/test-artifacts/runtime-reconcile-preview")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "runtime-reconcile-preview.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="warning",
            category="execution_retry_scheduled",
            title="Backtest retry scheduled",
            message="preview reconcile",
            symbol="AAPL",
            timeframe="1d",
        )
        app.assign_notification(event_id=created["event_id"], owner="operator", note="preview owner")
        app.resolve_notification(event_id=created["event_id"], note="preview resolved")

        with database_lock(str(db_path)):
            create_schema(str(db_path))
            repository = BacktestRunRepository(str(db_path))
            repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
            )

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET assigned_at = '',
                    acknowledged_at = '',
                    acknowledged_note = ''
                WHERE event_id = ?
                """,
                (created["event_id"],),
            )
        finally:
            connection.close()

        preview = app.preview_runtime_reconcile()
        notifications_before = app.recent_notification_events(limit=5)["notifications"]
        executions_before = app.recent_backtest_executions(limit=5)["executions"]

        self.assertEqual(preview["repaired_assignment_timestamps"], 1)
        self.assertEqual(preview["repaired_resolution_acknowledgements"], 1)
        self.assertEqual(preview["recovered_stale_executions"], 1)
        self.assertEqual(preview["total_candidates"], 3)
        self.assertEqual(notifications_before[0]["assigned_at"], "")
        self.assertEqual(notifications_before[0]["acknowledged_at"], "")
        self.assertEqual(executions_before[0]["status"], "running")

    def test_execution_retryable_failure_class_can_be_configured_by_name(self) -> None:
        """验证控制器可以按失败类名把普通异常提升为可重试异常。"""
        class CustomTransientError(RuntimeError):
            pass

        base_dir = Path("var/test-artifacts/retryable-class-config")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "retryable-class-config.duckdb"
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
                price += 1.0
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.7, 2),
                        "high": round(price + 0.5, 2),
                        "low": round(price - 1.0, 2),
                        "close": round(price, 2),
                        "volume": 2_000_000 + offset * 1000,
                    }
                )

        self._write_config(
            config_path,
            db_path,
            max_retry_attempts=2,
            execution_retryable_failure_classes="RetryableExecutionError,CustomTransientError",
        )
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")

        original_run_series = BacktestEngine.run_series
        call_state = {"count": 0}

        def flaky_run_series(self, bars, initial_equity):
            call_state["count"] += 1
            if call_state["count"] == 1:
                raise CustomTransientError("custom transient failure")
            return original_run_series(self, bars=bars, initial_equity=initial_equity)

        with patch.object(BacktestEngine, "run_series", new=flaky_run_series):
            persist_result = app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)

        executions = app.recent_backtest_executions(limit=5)["executions"]
        self.assertEqual(persist_result["status"], "completed")
        self.assertEqual(persist_result["attempts_used"], 2)
        self.assertEqual(executions[1]["failure_class"], "CustomTransientError")
        self.assertEqual(executions[1]["retry_decision"], "retry_scheduled")

    def test_protection_trigger_failure_class_blocks_next_execution(self) -> None:
        """验证配置里的即时保护失败类别会直接阻断下一次启动。"""
        base_dir = Path("var/test-artifacts/protection-trigger-class")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "protection-trigger-class.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            protection_mode_failure_threshold=5,
            protection_mode_cooldown_seconds=600,
            skip_run_on_protection_mode=True,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            execution_protection_trigger_failure_classes="DataCorruptionError",
        )
        app = QuantTradeApp(str(config_path))

        with database_lock(str(db_path)):
            create_schema(str(db_path))
            repository = BacktestRunRepository(str(db_path))
            execution_id = repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
            )
            repository.mark_execution_failed(
                execution_id=execution_id,
                error_message="detected corrupted broker snapshot",
                failure_class="DataCorruptionError",
                retry_decision="final_failure",
                retryable=False,
            )

        blocked = app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)

        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["execution"]["failure_class"], "ProtectionMode")
        self.assertIn("DataCorruptionError", blocked["execution"]["protection_reason"])

    def test_controller_health_surfaces_top_runtime_issues(self) -> None:
        """验证 controller health 能把最值得先看的异常集中输出。"""
        base_dir = Path("var/test-artifacts/controller-health")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "controller-health.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        self._write_config(
            config_path,
            db_path,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
            notification_assignment_sla_seconds=60,
        )
        app = QuantTradeApp(str(config_path))
        created = app._record_notification(
            severity="critical",
            category="execution_blocked",
            title="Backtest blocked by protection mode",
            message="controller health notification",
            symbol="AAPL",
            timeframe="1d",
        )
        app.assign_notification(event_id=created["event_id"], owner="operator", note="health owner")

        with database_lock(str(db_path)):
            create_schema(str(db_path))
            repository = BacktestRunRepository(str(db_path))
            repository.create_execution(
                request_id=str(uuid4()),
                symbol="AAPL",
                timeframe="1d",
                initial_equity=100_000.0,
            )

        connection = connect_database(str(db_path))
        try:
            connection.execute(
                """
                UPDATE notification_events
                SET assigned_at = ?
                WHERE event_id = ?
                """,
                ((datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(), created["event_id"]),
            )
        finally:
            connection.close()

        health = app.controller_health(runs_limit=5, events_limit=10)["controller_health"]

        self.assertGreaterEqual(health["summary"]["unacknowledged_critical_notifications"], 1)
        self.assertGreaterEqual(health["summary"]["sla_breached_notifications"], 1)
        self.assertGreaterEqual(health["summary"]["stale_execution_candidates"], 1)
        self.assertTrue(any(issue["code"] == "stale_execution_candidates" for issue in health["issues"]))

    def test_controller_monitor_emits_notification_for_stalled_live_runner(self) -> None:
        """验证 controller monitor 会把 stalled live runner 自动提升成通知。"""
        base_dir = Path("var/test-artifacts/controller-monitor-stalled")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "controller-monitor-stalled.duckdb"
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
            for offset in range(20):
                current = start + timedelta(days=offset)
                price += 0.9
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.4, 2),
                        "high": round(price + 0.5, 2),
                        "low": round(price - 0.8, 2),
                        "close": round(price, 2),
                        "volume": 2_150_000 + offset * 1000,
                    }
                )

        self._write_config(
            config_path,
            db_path,
            live_enabled=True,
            live_runner_id="paper-runner",
            live_poll_interval_seconds=30.0,
            live_max_cycles_per_run=1,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")
        cycle = app.live_run_cycle(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        cycle_id = cycle["cycle"]["cycle_id"]

        connection = connect_database(str(db_path))
        try:
            old_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()
            connection.execute(
                """
                UPDATE live_runner_cycles
                SET started_at = ?, finished_at = ?
                WHERE cycle_id = ?
                """,
                (old_timestamp, old_timestamp, cycle_id),
            )
        finally:
            connection.close()

        monitored = app.monitor_controller_health(runs_limit=5, events_limit=10)
        recent_notifications = app.recent_notification_events(limit=5)

        self.assertEqual(monitored["emitted_notifications"][0]["code"], "stalled_live_runner")
        self.assertEqual(monitored["emitted_notifications"][0]["category"], "controller_stalled_live_runner")
        self.assertEqual(monitored["emitted_notifications"][0]["notification"]["delivery_status"], "queued")
        self.assertEqual(recent_notifications["notifications"][0]["category"], "controller_stalled_live_runner")
        self.assertTrue(outbox_path.exists())

    def test_controller_monitor_emits_notification_for_stale_broker_snapshot(self) -> None:
        """验证 controller monitor 会把 stale broker snapshot 自动提升成通知。"""
        base_dir = Path("var/test-artifacts/controller-monitor-stale-broker")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "controller-monitor-stale-broker.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        account_path, positions_path, orders_path = self._write_broker_snapshots(base_dir)
        self._write_config(
            config_path,
            db_path,
            broker_enabled=True,
            broker_account_snapshot_path=str(account_path),
            broker_positions_snapshot_path=str(positions_path),
            broker_orders_snapshot_path=str(orders_path),
            broker_max_snapshot_age_seconds=60,
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )

        app = QuantTradeApp(str(config_path))
        sync_result = app.broker_sync(runner_id="paper-runner")
        sync_id = sync_result["detail"]["sync"]["sync_id"]
        connection = connect_database(str(db_path))
        try:
            connection.execute(
                "UPDATE broker_syncs SET synced_at = ? WHERE sync_id = ?",
                (datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(), sync_id),
            )
        finally:
            connection.close()

        monitored = app.monitor_controller_health(runs_limit=5, events_limit=10)
        recent_notifications = app.recent_notification_events(limit=5)

        self.assertEqual(monitored["emitted_notifications"][0]["code"], "stale_broker_snapshot")
        self.assertEqual(monitored["emitted_notifications"][0]["category"], "controller_stale_broker_snapshot")
        self.assertEqual(monitored["emitted_notifications"][0]["notification"]["delivery_status"], "queued")
        self.assertEqual(recent_notifications["notifications"][0]["category"], "controller_stale_broker_snapshot")
        self.assertTrue(outbox_path.exists())

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

    def test_live_runner_status_flags_stalled_runner(self) -> None:
        """验证 live runner 长时间没有新 cycle 时，会在 runner summary 和 controller health 里被标记为 stalled。"""
        base_dir = Path("var/test-artifacts/live-runner-stalled")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "live-runner-stalled.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 7, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(20):
                current = start + timedelta(days=offset)
                price += 0.9
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.4, 2),
                        "high": round(price + 0.5, 2),
                        "low": round(price - 0.8, 2),
                        "close": round(price, 2),
                        "volume": 2_150_000 + offset * 1000,
                    }
                )

        self._write_config(
            config_path,
            db_path,
            live_enabled=True,
            live_runner_id="paper-runner",
            live_poll_interval_seconds=30.0,
            live_max_cycles_per_run=1,
        )
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")
        cycle = app.live_run_cycle(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        cycle_id = cycle["cycle"]["cycle_id"]

        connection = connect_database(str(db_path))
        try:
            old_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()
            connection.execute(
                """
                UPDATE live_runner_cycles
                SET started_at = ?, finished_at = ?
                WHERE cycle_id = ?
                """,
                (old_timestamp, old_timestamp, cycle_id),
            )
        finally:
            connection.close()

        runner_summary = app.live_runner_status(limit=10)["summary"]
        controller_health = app.controller_health(runs_limit=5, events_limit=10)

        self.assertTrue(runner_summary[0]["stalled"])
        self.assertGreater(runner_summary[0]["last_cycle_age_seconds"], runner_summary[0]["stall_threshold_seconds"])
        self.assertEqual(controller_health["controller_health"]["summary"]["stalled_live_runners"], 1)
        self.assertIn(
            "stalled_live_runner",
            [issue["code"] for issue in controller_health["controller_health"]["issues"]],
        )

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

    def test_notification_delivery_backoff_uses_exponential_strategy_and_cap(self) -> None:
        """验证通知重投也支持独立的指数退避和最大等待时间封顶。"""
        base_dir = Path("var/test-artifacts/notification-backoff")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "notification-backoff.duckdb"
        config_path = base_dir / "settings.yaml"

        self._write_config(
            config_path,
            db_path,
            notification_delivery_retry_backoff_seconds=2.0,
            notification_delivery_retry_backoff_strategy="exponential",
            notification_delivery_retry_backoff_multiplier=3.0,
            notification_max_delivery_retry_backoff_seconds=10.0,
        )
        app = QuantTradeApp(str(config_path))

        self.assertEqual(app._compute_notification_delivery_backoff_seconds(1), 2.0)
        self.assertEqual(app._compute_notification_delivery_backoff_seconds(2), 6.0)
        self.assertEqual(app._compute_notification_delivery_backoff_seconds(3), 10.0)

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

    def test_broker_sync_imports_local_snapshot_files(self) -> None:
        """验证本地 broker 快照能被标准化、落库并完整查回。"""
        base_dir = Path("var/test-artifacts/broker-sync")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "broker-sync.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        account_path, positions_path, orders_path = self._write_broker_snapshots(base_dir)
        self._write_config(
            config_path,
            db_path,
            broker_enabled=True,
            broker_account_snapshot_path=str(account_path),
            broker_positions_snapshot_path=str(positions_path),
            broker_orders_snapshot_path=str(orders_path),
        )

        app = QuantTradeApp(str(config_path))
        sync_result = app.broker_sync(runner_id="paper-runner")
        recent_syncs = app.recent_broker_syncs(limit=5)
        detail = app.broker_sync_detail(sync_id=sync_result["detail"]["sync"]["sync_id"])

        self.assertEqual(sync_result["status"], "completed")
        self.assertEqual(sync_result["detail"]["sync"]["provider"], "local_file")
        self.assertEqual(sync_result["detail"]["sync"]["account_id"], "paper-account")
        self.assertEqual(sync_result["detail"]["sync"]["position_count"], 2)
        self.assertEqual(sync_result["detail"]["sync"]["order_count"], 1)
        self.assertEqual(sync_result["detail"]["sync"]["runner_id"], "paper-runner")
        self.assertEqual(len(sync_result["detail"]["positions"]), 2)
        self.assertEqual(len(sync_result["detail"]["orders"]), 1)
        self.assertEqual(recent_syncs["broker_syncs"][0]["sync_id"], sync_result["detail"]["sync"]["sync_id"])
        self.assertEqual(detail["detail"]["sync"]["sync_id"], sync_result["detail"]["sync"]["sync_id"])
        self.assertEqual(detail["detail"]["positions"][0]["symbol"], "AAPL")
        self.assertEqual(detail["detail"]["orders"][0]["broker_order_id"], "broker-order-1")

    def test_history_payload_includes_recent_broker_syncs(self) -> None:
        """验证 history payload 会把 broker 同步摘要和最近同步列表一起带给前端。"""
        base_dir = Path("var/test-artifacts/broker-history")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "broker-history.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 8, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(12):
                current = start + timedelta(days=offset)
                price += 0.8
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.4, 2),
                        "high": round(price + 0.5, 2),
                        "low": round(price - 0.9, 2),
                        "close": round(price, 2),
                        "volume": 2_000_000 + offset * 1000,
                    }
                )

        account_path, positions_path, orders_path = self._write_broker_snapshots(base_dir)
        self._write_config(
            config_path,
            db_path,
            broker_enabled=True,
            broker_account_snapshot_path=str(account_path),
            broker_positions_snapshot_path=str(positions_path),
            broker_orders_snapshot_path=str(orders_path),
        )
        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")
        app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        app.broker_sync(runner_id="paper-runner")

        history_payload = app.dashboard_history(runs_limit=5, events_limit=10)

        self.assertIn("recent_broker_syncs", history_payload)
        self.assertEqual(history_payload["history_summary"]["total_broker_syncs"], 1)
        self.assertEqual(history_payload["history_summary"]["failed_broker_syncs"], 0)
        self.assertEqual(history_payload["history_summary"]["latest_broker_provider"], "local_file")
        self.assertEqual(history_payload["history_summary"]["latest_broker_positions"], 2)
        self.assertEqual(history_payload["history_summary"]["latest_broker_orders"], 1)
        self.assertGreater(history_payload["history_summary"]["latest_broker_equity"], 0.0)
        self.assertEqual(history_payload["recent_broker_syncs"][0]["runner_id"], "paper-runner")
        self.assertIn("broker_health", history_payload)

    def test_broker_health_flags_stale_snapshot_and_controller_issue(self) -> None:
        """验证过旧的 broker 快照会进入 broker health 和 controller health 视图。"""
        base_dir = Path("var/test-artifacts/broker-health-stale")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "broker-health-stale.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        account_path, positions_path, orders_path = self._write_broker_snapshots(base_dir)
        self._write_config(
            config_path,
            db_path,
            broker_enabled=True,
            broker_account_snapshot_path=str(account_path),
            broker_positions_snapshot_path=str(positions_path),
            broker_orders_snapshot_path=str(orders_path),
            broker_max_snapshot_age_seconds=60,
        )

        app = QuantTradeApp(str(config_path))
        sync_result = app.broker_sync(runner_id="paper-runner")
        sync_id = sync_result["detail"]["sync"]["sync_id"]
        connection = connect_database(str(db_path))
        try:
            connection.execute(
                "UPDATE broker_syncs SET synced_at = ? WHERE sync_id = ?",
                (datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(), sync_id),
            )
        finally:
            connection.close()

        broker_health = app.broker_health(limit=5)
        controller_health = app.controller_health(runs_limit=5, events_limit=5)

        self.assertTrue(broker_health["broker_health"]["stale"])
        self.assertEqual(broker_health["broker_health"]["max_snapshot_age_seconds"], 60)
        self.assertGreater(broker_health["broker_health"]["snapshot_age_seconds"], 60)
        self.assertIn(
            "stale_broker_snapshot",
            [issue["code"] for issue in controller_health["controller_health"]["issues"]],
        )

    def test_broker_health_flags_failed_latest_sync(self) -> None:
        """验证最近一次 broker 同步失败时，会显式进入 broker health 失败状态。"""
        base_dir = Path("var/test-artifacts/broker-health-failed")
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / "broker-health-failed.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        missing_account_path = base_dir / "missing-account.json"
        missing_positions_path = base_dir / "missing-positions.json"
        missing_orders_path = base_dir / "missing-orders.json"
        self._write_config(
            config_path,
            db_path,
            broker_enabled=True,
            broker_account_snapshot_path=str(missing_account_path),
            broker_positions_snapshot_path=str(missing_positions_path),
            broker_orders_snapshot_path=str(missing_orders_path),
            broker_max_snapshot_age_seconds=300,
        )

        app = QuantTradeApp(str(config_path))
        sync_result = app.broker_sync(runner_id="paper-runner")
        broker_health = app.broker_health(limit=5)
        controller_health = app.controller_health(runs_limit=5, events_limit=5)

        self.assertEqual(sync_result["status"], "failed")
        self.assertTrue(broker_health["broker_health"]["failed"])
        self.assertEqual(broker_health["broker_health"]["latest_status"], "failed")
        self.assertEqual(broker_health["broker_health"]["failed_sync_count"], 1)
        self.assertIn(
            "failed_broker_sync",
            [issue["code"] for issue in controller_health["controller_health"]["issues"]],
        )

    def test_broker_reconcile_reports_drift_against_latest_run(self) -> None:
        """验证 broker reconcile 会把最新本地运行和 broker 快照之间的差异显式列出来。"""
        base_dir = Path("var/test-artifacts/broker-reconcile")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "broker-reconcile.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 9, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(15):
                current = start + timedelta(days=offset)
                price += 1.0
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.5, 2),
                        "high": round(price + 0.6, 2),
                        "low": round(price - 0.9, 2),
                        "close": round(price, 2),
                        "volume": 2_200_000 + offset * 1000,
                    }
                )

        account_path, positions_path, orders_path = self._write_broker_snapshots(base_dir)
        self._write_config(
            config_path,
            db_path,
            broker_enabled=True,
            broker_account_snapshot_path=str(account_path),
            broker_positions_snapshot_path=str(positions_path),
            broker_orders_snapshot_path=str(orders_path),
        )

        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")
        app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        app.broker_sync(runner_id="paper-runner")

        reconcile = app.broker_reconcile(limit=10)
        controller_health = app.controller_health(runs_limit=5, events_limit=10)

        self.assertEqual(reconcile["broker_reconcile"]["status"], "drift")
        self.assertGreater(reconcile["broker_reconcile"]["mismatch_count"], 0)
        self.assertEqual(len(reconcile["broker_reconcile"]["rows"]), 4)
        self.assertTrue(all("threshold" in row for row in reconcile["broker_reconcile"]["rows"]))
        self.assertTrue(any(bool(row["breached"]) for row in reconcile["broker_reconcile"]["rows"]))
        self.assertIn("drift detected", reconcile["broker_reconcile"]["notes"][0])
        self.assertIn(
            "broker_reconcile_drift",
            [issue["code"] for issue in controller_health["controller_health"]["issues"]],
        )

    def test_broker_reconcile_respects_configured_thresholds(self) -> None:
        """验证 broker reconcile 会把“有差异但未越阈”的情况视为可容忍偏差，而不是直接报 drift。"""
        base_dir = Path("var/test-artifacts/broker-reconcile-thresholds")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "broker-reconcile-thresholds.duckdb"
        config_path = base_dir / "settings.yaml"
        if db_path.exists():
            db_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 10, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(15):
                current = start + timedelta(days=offset)
                price += 1.0
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.5, 2),
                        "high": round(price + 0.6, 2),
                        "low": round(price - 0.9, 2),
                        "close": round(price, 2),
                        "volume": 2_200_000 + offset * 1000,
                    }
                )

        account_path, positions_path, orders_path = self._write_broker_snapshots(base_dir)
        self._write_config(
            config_path,
            db_path,
            broker_enabled=True,
            broker_account_snapshot_path=str(account_path),
            broker_positions_snapshot_path=str(positions_path),
            broker_orders_snapshot_path=str(orders_path),
            broker_equity_drift_threshold=50000.0,
            broker_cash_drift_threshold=60000.0,
            broker_position_count_drift_threshold=3,
            broker_open_order_drift_threshold=2,
        )

        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")
        app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        app.broker_sync(runner_id="paper-runner")

        reconcile = app.broker_reconcile(limit=10)
        self.assertEqual(reconcile["broker_reconcile"]["status"], "aligned")
        self.assertEqual(reconcile["broker_reconcile"]["mismatch_count"], 0)
        self.assertTrue(all(not bool(row["breached"]) for row in reconcile["broker_reconcile"]["rows"]))
        self.assertIn("within configured thresholds", reconcile["broker_reconcile"]["notes"][0])

    def test_broker_sync_emits_notification_when_reconcile_drift_is_detected(self) -> None:
        """验证 broker sync 完成后，如果对账越过阈值，会自动生成 drift 通知。"""
        base_dir = Path("var/test-artifacts/broker-reconcile-notification")
        base_dir.mkdir(parents=True, exist_ok=True)
        csv_path = base_dir / "bars.csv"
        db_path = base_dir / "broker-reconcile-notification.duckdb"
        config_path = base_dir / "settings.yaml"
        outbox_path = base_dir / "outbox.jsonl"
        if db_path.exists():
            db_path.unlink()
        if outbox_path.exists():
            outbox_path.unlink()

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            start = datetime(2024, 11, 1, tzinfo=timezone.utc)
            price = 100.0
            for offset in range(15):
                current = start + timedelta(days=offset)
                price += 1.0
                writer.writerow(
                    {
                        "timestamp": current.isoformat(),
                        "open": round(price - 0.5, 2),
                        "high": round(price + 0.6, 2),
                        "low": round(price - 0.9, 2),
                        "close": round(price, 2),
                        "volume": 2_200_000 + offset * 1000,
                    }
                )

        account_path, positions_path, orders_path = self._write_broker_snapshots(base_dir)
        self._write_config(
            config_path,
            db_path,
            broker_enabled=True,
            broker_account_snapshot_path=str(account_path),
            broker_positions_snapshot_path=str(positions_path),
            broker_orders_snapshot_path=str(orders_path),
            notification_enabled=True,
            notification_outbox_path=str(outbox_path),
        )

        app = QuantTradeApp(str(config_path))
        app.import_csv(str(csv_path), symbol="AAPL", timeframe="1d")
        app.persist_backtest_run(symbol="AAPL", timeframe="1d", initial_equity=100_000.0)
        sync_result = app.broker_sync(runner_id="paper-runner")
        recent_notifications = app.recent_notification_events(limit=5)

        self.assertEqual(sync_result["status"], "completed")
        self.assertIsNotNone(sync_result["notification"])
        self.assertEqual(sync_result["notification"]["delivery_status"], "queued")
        self.assertTrue(outbox_path.exists())
        self.assertEqual(recent_notifications["notifications"][0]["category"], "broker_reconcile_drift")

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
