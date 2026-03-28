"""应用装配层。

这个文件相当于整个 QuantTrade 的“总调度台”：
1. 读取配置；
2. 初始化日志和数据目录；
3. 把策略、风控、执行、数据仓储这些模块拼起来；
4. 对外暴露给 CLI 调用的高层能力。

小白可以把它理解成“把所有零件接线后，提供一组可直接操作的按钮”。
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from quanttrade.audit.logger import configure_logging
from quanttrade.backtest.engine import BacktestEngine
from quanttrade.backtest.exporter import export_backtest_result
from quanttrade.config.loader import load_settings
from quanttrade.core.exceptions import NonRetryableExecutionError, RetryableExecutionError
from quanttrade.core.types import AccountState, MarketBar, PositionState
from quanttrade.dashboard.service import build_dashboard_payload, build_history_payload
from quanttrade.dashboard.html import render_dashboard_html, render_history_html
from quanttrade.data.importer import import_bars_from_csv
from quanttrade.data.repository import BacktestRunRepository, BarRepository
from quanttrade.data.schema import create_schema
from quanttrade.data.storage import database_lock, ensure_data_dirs, execution_lock
from quanttrade.execution.simulator import SimulatedExecutionEngine
from quanttrade.notification.service import (
    append_notification_to_outbox,
    dispatch_notification_via_adapter,
    should_emit_notification,
)
from quanttrade.risk.engine import RiskEngine
from quanttrade.strategies.atr_dtf import AtrDynamicTrendFollowingStrategy

LOGGER = logging.getLogger(__name__)

_NOTIFICATION_SEVERITY_RANK = {
    "info": 10,
    "warning": 20,
    "error": 30,
    "critical": 40,
}


def _parse_csv_flag_set(raw_value: str) -> set[str]:
    """把逗号分隔配置解析成去重后的名称集合。"""
    return {
        item.strip()
        for item in str(raw_value or "").split(",")
        if item.strip()
    }


class QuantTradeApp:
    """QuantTrade 的高层门面对象。

    CLI 不直接操作底层模块，而是统一通过这个类调用。
    这样做的好处是：
    1. 命令行层只负责接收参数和打印结果；
    2. 真正的业务流程集中在这里，更容易维护；
    3. 以后如果接 Web API，也可以继续复用这些方法。
    """

    def __init__(self, config_path: str) -> None:
        """加载配置，并提前把运行所需环境准备好。"""
        self.settings = load_settings(config_path)
        configure_logging()
        ensure_data_dirs(self.settings.data.duckdb_path)

    def doctor(self) -> dict[str, object]:
        """返回当前生效配置，方便确认系统到底会按什么参数运行。"""
        return {
            "app": asdict(self.settings.app),
            "strategy": asdict(self.settings.strategy),
            "risk": asdict(self.settings.risk),
            "data_path": self.settings.data.duckdb_path,
            "data_backend": self.settings.data.backend,
            "execution": asdict(self.settings.execution),
            "live": asdict(self.settings.live),
            "notification": asdict(self.settings.notification),
        }

    def run_sample(self) -> dict[str, object]:
        """运行一个人造样例 bar，用来快速验证主链路是否能打通。"""
        strategy = AtrDynamicTrendFollowingStrategy(self.settings.strategy)
        risk_engine = RiskEngine(self.settings.risk)
        execution_engine = SimulatedExecutionEngine(self.settings.execution)
        engine = BacktestEngine(strategy, risk_engine, execution_engine)

        # 这里故意构造一根“看起来会触发入场”的 bar，方便快速做冒烟测试。
        market_bar = MarketBar(
            timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=104.0,
            low=99.0,
            close=105.0,
            volume=2_000_000,
            atr=2.0,
            adx=30.0,
            donchian_high=103.0,
            donchian_low=96.0,
        )
        account_state = AccountState(equity=100_000.0, cash=100_000.0)
        position_state = PositionState(symbol=self.settings.strategy.symbol)
        result = engine.run_once(market_bar, account_state, position_state)
        return asdict(result)

    def import_csv(self, csv_path: str, symbol: str, timeframe: str = "1d") -> dict[str, object]:
        """把 CSV 行情导入数据库。

        这里先拿数据库锁，是为了避免导入和回测同时写同一个 DuckDB 文件时产生冲突。
        """
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            inserted = import_bars_from_csv(
                csv_path=csv_path,
                db_path=self.settings.data.duckdb_path,
                symbol=symbol,
                timeframe=timeframe,
            )
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "rows_inserted": inserted,
            "data_path": self.settings.data.duckdb_path,
        }

    def backtest_symbol(self, symbol: str, timeframe: str = "1d", initial_equity: float = 100_000.0) -> dict[str, object]:
        """对单个标的执行一次不落库的历史回测。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BarRepository(self.settings.data.duckdb_path)
            bars = repository.fetch_bars(symbol=symbol, timeframe=timeframe)
        # 策略对象会直接读取 config 里的 symbol，所以这里要把本次调用参数同步进去。
        strategy_config = self.settings.strategy
        strategy_config.symbol = symbol
        strategy = AtrDynamicTrendFollowingStrategy(strategy_config)
        risk_engine = RiskEngine(self.settings.risk)
        execution_engine = SimulatedExecutionEngine(self.settings.execution)
        engine = BacktestEngine(strategy, risk_engine, execution_engine)
        result = engine.run_series(bars=bars, initial_equity=initial_equity)
        return asdict(result)

    def _effective_live_runner_id(self, runner_id: str = "") -> str:
        """返回本次 live cycle 应该使用的 runner 标识。"""
        normalized = str(runner_id or "").strip()
        if normalized:
            return normalized
        fallback = str(self.settings.live.runner_id or "").strip()
        return fallback or "local-default"

    def _classify_execution_error(self, exc: Exception) -> dict[str, object]:
        """把一次执行异常翻译成运行控制器可理解的决策信息。

        这一步很关键，因为运行控制器真正需要的不是“异常字符串”，而是：
        1. 这类错误是否值得再试；
        2. 如果不再试，是因为输入有问题，还是因为系统主动阻断；
        3. 日志和持久化里应该如何描述这次判断。
        """
        failure_class = exc.__class__.__name__
        retryable_class_names = _parse_csv_flag_set(self.settings.execution.retryable_failure_classes)
        non_retryable_class_names = _parse_csv_flag_set(self.settings.execution.non_retryable_failure_classes)

        if failure_class in retryable_class_names:
            return {
                "retryable": True,
                "failure_class": failure_class,
                "log_reason": str(exc),
            }
        if failure_class in non_retryable_class_names:
            return {
                "retryable": False,
                "failure_class": failure_class,
                "log_reason": str(exc),
            }
        if isinstance(exc, RetryableExecutionError):
            return {
                "retryable": True,
                "failure_class": failure_class,
                "log_reason": str(exc),
            }
        if isinstance(exc, NonRetryableExecutionError):
            return {
                "retryable": False,
                "failure_class": failure_class,
                "log_reason": str(exc),
            }
        return {
            "retryable": False,
            "failure_class": failure_class,
            "log_reason": str(exc),
        }

    def _notification_assignment_sla_overrides(self) -> dict[str, int]:
        """返回按严重级别覆写后的通知 SLA 配置。"""
        return {
            "warning": max(int(self.settings.notification.assignment_sla_warning_seconds), 0),
            "error": max(int(self.settings.notification.assignment_sla_error_seconds), 0),
            "critical": max(int(self.settings.notification.assignment_sla_critical_seconds), 0),
        }

    def _protection_trigger_failure_classes(self) -> set[str]:
        """整理哪些失败类别应该立即触发保护模式。"""
        return _parse_csv_flag_set(self.settings.execution.protection_trigger_failure_classes)

    def _match_notifications_by_event_ids(
        self,
        event_ids: list[str],
        refreshed: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """按输入顺序返回批量动作命中的通知。"""
        normalized = [item.strip() for item in event_ids if item.strip()]
        by_id = {str(item.get("event_id", "")): item for item in refreshed}
        return [by_id[event_id] for event_id in normalized if event_id in by_id]

    def reconcile_runtime_state(self) -> dict[str, object]:
        """修复最常见的写路径不一致状态。"""
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            repaired_assignments = repository.backfill_notification_assigned_at()
            repaired_resolution_acknowledgements = repository.backfill_notification_acknowledged_at_from_resolution()
            recovered_stale_executions = repository.recover_all_stale_executions()
        return {
            "repaired_assignment_timestamps": repaired_assignments,
            "repaired_resolution_acknowledgements": repaired_resolution_acknowledgements,
            "recovered_stale_executions": recovered_stale_executions,
        }

    def preview_runtime_reconcile(self) -> dict[str, object]:
        """只统计还能自动修多少脏状态，不真正落修复。"""
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            repaired_assignments = repository.count_notification_assignment_backfill_candidates()
            repaired_resolution_acknowledgements = repository.count_notification_resolution_ack_backfill_candidates()
            recovered_stale_executions = repository.count_stale_executions()
        return {
            "repaired_assignment_timestamps": repaired_assignments,
            "repaired_resolution_acknowledgements": repaired_resolution_acknowledgements,
            "recovered_stale_executions": recovered_stale_executions,
            "total_candidates": (
                repaired_assignments
                + repaired_resolution_acknowledgements
                + recovered_stale_executions
            ),
        }

    def _maybe_reconcile_runtime_state(self, *, recover_stale_executions: bool = True) -> dict[str, object]:
        """按配置决定是否在写操作前自动做轻量修复。"""
        if not bool(self.settings.execution.reconcile_on_write):
            return {
                "repaired_assignment_timestamps": 0,
                "repaired_resolution_acknowledgements": 0,
                "recovered_stale_executions": 0,
            }
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            repaired_assignments = repository.backfill_notification_assigned_at()
            repaired_resolution_acknowledgements = repository.backfill_notification_acknowledged_at_from_resolution()
            recovered_execution_count = 0
            if recover_stale_executions:
                recovered_execution_count = repository.recover_all_stale_executions()
        return {
            "repaired_assignment_timestamps": repaired_assignments,
            "repaired_resolution_acknowledgements": repaired_resolution_acknowledgements,
            "recovered_stale_executions": recovered_execution_count,
        }

    def _compute_retry_backoff_seconds(self, attempt_number: int) -> float:
        """根据配置计算本次重试前应该等待多久。

        小白可以把这里理解成“控制器决定先停多久再撞下一次”：
        1. `retry_backoff_seconds` 是基础等待时长；
        2. `retry_backoff_strategy` 决定等待是线性增加，还是指数级增加；
        3. `retry_backoff_multiplier` 只在指数退避时起作用；
        4. `max_retry_backoff_seconds` 用来给等待时间封顶，避免越退越久。
        """
        base_delay = max(float(self.settings.execution.retry_backoff_seconds), 0.0)
        if base_delay <= 0:
            return 0.0

        strategy = str(self.settings.execution.retry_backoff_strategy or "linear").strip().lower()
        multiplier = max(float(self.settings.execution.retry_backoff_multiplier), 1.0)
        capped_max = max(float(self.settings.execution.max_retry_backoff_seconds), 0.0)
        normalized_attempt = max(int(attempt_number), 1)

        if strategy == "exponential":
            delay = base_delay * (multiplier ** max(normalized_attempt - 1, 0))
        else:
            # 任何未知策略都退回线性模式，保证控制流可预测，而不是因为拼写问题直接失效。
            delay = base_delay * normalized_attempt

        if capped_max > 0:
            return min(delay, capped_max)
        return delay

    def _compute_notification_delivery_backoff_seconds(self, attempt_number: int) -> float:
        """根据通知配置计算下一次最早允许重投的等待时间。

        这里和 execution retry 的思路一致，但服务对象不同：
        - execution retry 面向“任务本身还能不能继续跑”；
        - notification retry 面向“告警有没有必要立刻再撞一次渠道”。

        把两者拆开配置，是为了避免出现这种情况：
        回测任务适合快重试，但通知渠道反而需要更慢、更克制的重投节奏。
        """
        base_delay = max(float(self.settings.notification.delivery_retry_backoff_seconds), 0.0)
        if base_delay <= 0:
            return 0.0

        strategy = str(self.settings.notification.delivery_retry_backoff_strategy or "linear").strip().lower()
        multiplier = max(float(self.settings.notification.delivery_retry_backoff_multiplier), 1.0)
        capped_max = max(float(self.settings.notification.max_delivery_retry_backoff_seconds), 0.0)
        normalized_attempt = max(int(attempt_number), 1)

        if strategy == "exponential":
            delay = base_delay * (multiplier ** max(normalized_attempt - 1, 0))
        else:
            delay = base_delay * normalized_attempt

        if capped_max > 0:
            return min(delay, capped_max)
        return delay

    def _build_notification_key(
        self,
        *,
        category: str,
        title: str,
        symbol: str,
        timeframe: str,
    ) -> str:
        """构造通知去重键。

        这里故意不把 `request_id` / `execution_id` 拼进去，
        因为静默窗口想解决的是“同类告警在短时间内刷屏”，
        而不是区分每一次底层尝试。
        """
        return "|".join(
            [
                str(category).strip().lower(),
                str(title).strip().lower(),
                str(symbol).strip().upper(),
                str(timeframe).strip().lower(),
            ]
        )

    def _notification_meets_escalation_threshold(self, severity: str) -> bool:
        """判断一条通知是否达到了当前升级策略要求的最低级别。"""
        current = _NOTIFICATION_SEVERITY_RANK.get(str(severity).strip().lower(), 0)
        threshold = _NOTIFICATION_SEVERITY_RANK.get(
            str(self.settings.notification.escalation_min_severity).strip().lower(),
            40,
        )
        return current >= threshold

    def _record_notification(
        self,
        *,
        severity: str,
        category: str,
        title: str,
        message: str,
        symbol: str = "",
        timeframe: str = "",
        run_id: str = "",
        execution_id: str = "",
        request_id: str = "",
    ) -> dict[str, object]:
        """记录一条通知事件，并在满足规则时写入本地 outbox。

        这里的设计故意偏“骨架化”：
        - 不直接耦合 Telegram SDK；
        - 先把事件写入数据库和 JSONL outbox；
        - 后续真正接外部服务时，只需要消费 outbox。
        """
        delivery_status = "suppressed"
        delivery_target = ""
        notification_key = self._build_notification_key(
            category=category,
            title=title,
            symbol=symbol,
            timeframe=timeframe,
        )
        silence_window_seconds = max(int(self.settings.notification.silence_window_seconds), 0)
        now_iso = datetime.now(timezone.utc).isoformat()
        silenced_until = ""
        if silence_window_seconds > 0:
            silenced_until = (datetime.now(timezone.utc) + timedelta(seconds=silence_window_seconds)).isoformat()
        if self.settings.notification.enabled and should_emit_notification(self.settings.notification, severity):
            with database_lock(self.settings.data.duckdb_path):
                # 通知系统现在已经能脱离回测主流程单独使用，所以这里不能假设表一定已经由别的流程建好。
                create_schema(self.settings.data.duckdb_path)
                repository = BacktestRunRepository(self.settings.data.duckdb_path)
                if silence_window_seconds > 0:
                    active = repository.fetch_active_notification_for_key(notification_key=notification_key, current_time=now_iso)
                    if active is not None:
                        repository.mark_notification_duplicate_suppressed(
                            event_id=str(active.get("event_id", "")),
                            silenced_until=silenced_until,
                            last_suppressed_at=now_iso,
                        )
                        return {
                            "event_id": str(active.get("event_id", "")),
                            "delivery_status": "silenced_duplicate",
                            "delivery_target": str(active.get("delivery_target", "")),
                        }
            outbox_payload = {
                "severity": severity,
                "category": category,
                "title": title,
                "message": message,
                "symbol": symbol,
                "timeframe": timeframe,
                "run_id": run_id,
                "execution_id": execution_id,
                "request_id": request_id,
                "provider": self.settings.notification.provider,
                "notification_key": notification_key,
            }
            delivery_target = append_notification_to_outbox(self.settings.notification, outbox_payload)
            delivery_status = "queued"
        elif self.settings.notification.enabled:
            delivery_status = "filtered"

        with database_lock(self.settings.data.duckdb_path):
            # 通知系统现在已经能脱离回测主流程单独使用，所以这里不能假设表一定已经由别的流程建好。
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            event_id = repository.save_notification_event(
                severity=severity,
                category=category,
                title=title,
                message=message,
                provider=self.settings.notification.provider,
                delivery_status=delivery_status,
                delivery_target=delivery_target,
                symbol=symbol,
                timeframe=timeframe,
                run_id=run_id,
                execution_id=execution_id,
                request_id=request_id,
                notification_key=notification_key,
                silenced_until=silenced_until,
            )
        return {
            "event_id": event_id,
            "delivery_status": delivery_status,
            "delivery_target": delivery_target,
        }

    def persist_backtest_run(
        self,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
    ) -> dict[str, object]:
        """执行一次会落库的回测，并记录执行生命周期。

        这一步比 `backtest_symbol` 多了两层保护：
        1. execution_lock：阻止同标的同周期被重复触发；
        2. backtest_executions：记录这次运行是开始了、完成了、失败了还是中断恢复了。
        """
        max_retry_attempts = max(int(self.settings.execution.max_retry_attempts), 1)
        retry_backoff_strategy = str(self.settings.execution.retry_backoff_strategy or "linear").strip().lower()
        protection_threshold = max(int(self.settings.execution.protection_mode_failure_threshold), 1)
        protection_cooldown_seconds = max(int(self.settings.execution.protection_mode_cooldown_seconds), 0)
        skip_run_on_protection_mode = bool(self.settings.execution.skip_run_on_protection_mode)
        request_id = str(uuid4())
        execution_id = ""
        recovered_executions = 0
        run_id = ""
        payload: dict[str, object] = {}
        last_error: str | None = None
        attempts_used = 0
        with execution_lock(self.settings.data.duckdb_path, symbol=symbol, timeframe=timeframe, blocking=False):
            self._maybe_reconcile_runtime_state(recover_stale_executions=False)
            for _ in range(max_retry_attempts):
                attempts_used += 1
                LOGGER.info(
                    "starting persisted backtest request_id=%s symbol=%s timeframe=%s attempt=%s/%s",
                    request_id,
                    symbol,
                    timeframe,
                    attempts_used,
                    max_retry_attempts,
                )
                with database_lock(self.settings.data.duckdb_path):
                    create_schema(self.settings.data.duckdb_path)
                    repository = BacktestRunRepository(self.settings.data.duckdb_path)
                    # 如果上一次运行异常中断，先把旧的 running 状态修正为 abandoned。
                    recovered_executions += repository.recover_stale_executions(symbol=symbol, timeframe=timeframe)
                    execution_id = repository.create_execution(
                        request_id=request_id,
                        symbol=symbol,
                        timeframe=timeframe,
                        initial_equity=initial_equity,
                        recovered_execution_count=recovered_executions,
                        protection_mode_failure_threshold=protection_threshold,
                        protection_mode_cooldown_seconds=protection_cooldown_seconds,
                        protection_trigger_failure_classes=self._protection_trigger_failure_classes(),
                    )
                    execution_detail = repository.fetch_execution_detail(execution_id)

                execution = execution_detail["execution"] if execution_detail else {}
                if (not execution.get("protection_mode")) and str(execution.get("protection_reason", "")).startswith(
                    "protection cooldown expired"
                ):
                    LOGGER.info(
                        "resuming backtest request_id=%s execution_id=%s after protection cooldown expired: %s",
                        request_id,
                        execution_id,
                        execution.get("protection_reason", ""),
                    )
                    self._record_notification(
                        severity="warning",
                        category="protection_resumed",
                        title="Backtest resumed after protection cooldown",
                        message=str(execution.get("protection_reason", "")),
                        symbol=symbol,
                        timeframe=timeframe,
                        execution_id=execution_id,
                        request_id=request_id,
                    )
                if execution.get("protection_mode") and skip_run_on_protection_mode:
                    LOGGER.warning(
                        "blocking backtest request_id=%s execution_id=%s because protection mode is active: %s",
                        request_id,
                        execution_id,
                        execution.get("protection_reason", ""),
                    )
                    with database_lock(self.settings.data.duckdb_path):
                        repository = BacktestRunRepository(self.settings.data.duckdb_path)
                        repository.mark_execution_blocked(
                            execution_id=execution_id,
                            reason=str(execution.get("protection_reason") or "blocked by protection mode"),
                        )
                    self._record_notification(
                        severity="critical",
                        category="execution_blocked",
                        title="Backtest blocked by protection mode",
                        message=str(execution.get("protection_reason") or "blocked by protection mode"),
                        symbol=symbol,
                        timeframe=timeframe,
                        execution_id=execution_id,
                        request_id=request_id,
                    )
                    latest_execution = self.execution_detail(execution_id=execution_id)["detail"]
                    return {
                        "status": "blocked",
                        "message": "backtest execution was blocked by protection mode",
                        "request_id": request_id,
                        "execution_id": execution_id,
                        "run_id": None,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "bars_processed": 0,
                        "metrics": {},
                        "recovered_executions": recovered_executions,
                        "attempts_used": attempts_used,
                        "retry_count": max(attempts_used - 1, 0),
                        "execution": latest_execution["execution"] if latest_execution else execution,
                    }

                with database_lock(self.settings.data.duckdb_path):
                    bar_repository = BarRepository(self.settings.data.duckdb_path)
                    bars = bar_repository.fetch_bars(symbol=symbol, timeframe=timeframe)

                strategy_config = self.settings.strategy
                strategy_config.symbol = symbol
                strategy = AtrDynamicTrendFollowingStrategy(strategy_config)
                risk_engine = RiskEngine(self.settings.risk)
                execution_engine = SimulatedExecutionEngine(self.settings.execution)
                engine = BacktestEngine(strategy, risk_engine, execution_engine)
                try:
                    payload = asdict(engine.run_series(bars=bars, initial_equity=initial_equity))
                    with database_lock(self.settings.data.duckdb_path):
                        repository = BacktestRunRepository(self.settings.data.duckdb_path)
                        run_id = repository.save_run(symbol=symbol, timeframe=timeframe, payload=payload)
                        repository.mark_execution_completed(execution_id=execution_id, run_id=run_id)
                    LOGGER.info(
                        "completed persisted backtest request_id=%s execution_id=%s run_id=%s attempt=%s",
                        request_id,
                        execution_id,
                        run_id,
                        attempts_used,
                    )
                    if attempts_used > 1:
                        self._record_notification(
                            severity="warning",
                            category="execution_recovered",
                            title="Backtest succeeded after retry",
                            message=(
                                f"request {request_id} completed after {attempts_used} attempts; "
                                f"final run_id={run_id}"
                            ),
                            symbol=symbol,
                            timeframe=timeframe,
                            run_id=run_id,
                            execution_id=execution_id,
                            request_id=request_id,
                        )
                    break
                except Exception as exc:
                    error_meta = self._classify_execution_error(exc)
                    last_error = str(error_meta["log_reason"])
                    retryable = bool(error_meta["retryable"])
                    retry_decision = "retry_scheduled" if retryable and attempts_used < max_retry_attempts else "final_failure"
                    with database_lock(self.settings.data.duckdb_path):
                        repository = BacktestRunRepository(self.settings.data.duckdb_path)
                        repository.mark_execution_failed(
                            execution_id=execution_id,
                            error_message=last_error,
                            retryable=retryable,
                            retry_decision=retry_decision,
                            failure_class=str(error_meta["failure_class"]),
                        )
                    if retry_decision == "retry_scheduled":
                        self._record_notification(
                            severity="warning",
                            category="execution_retry_scheduled",
                            title="Backtest retry scheduled",
                            message=(
                                f"request {request_id} execution {execution_id} will retry after "
                                f"{error_meta['failure_class']}: {last_error}"
                            ),
                            symbol=symbol,
                            timeframe=timeframe,
                            execution_id=execution_id,
                            request_id=request_id,
                        )
                        backoff_seconds = self._compute_retry_backoff_seconds(attempts_used)
                        LOGGER.warning(
                            "retrying persisted backtest request_id=%s execution_id=%s after retryable failure class=%s attempt=%s/%s strategy=%s backoff_seconds=%.3f reason=%s",
                            request_id,
                            execution_id,
                            error_meta["failure_class"],
                            attempts_used,
                            max_retry_attempts,
                            retry_backoff_strategy,
                            backoff_seconds,
                            last_error,
                        )
                        if backoff_seconds > 0:
                            # 这里显式 sleep，不是为了模拟外部系统，而是为了把“退避策略”真正落实成控制动作。
                            time.sleep(backoff_seconds)
                        continue
                    LOGGER.error(
                        "stopping persisted backtest request_id=%s execution_id=%s after non-retryable or final failure class=%s attempt=%s/%s reason=%s",
                        request_id,
                        execution_id,
                        error_meta["failure_class"],
                        attempts_used,
                        max_retry_attempts,
                        last_error,
                    )
                    self._record_notification(
                        severity="critical",
                        category="execution_final_failure",
                        title="Backtest execution failed",
                        message=(
                            f"request {request_id} execution {execution_id} stopped after "
                            f"{error_meta['failure_class']}: {last_error}"
                        ),
                        symbol=symbol,
                        timeframe=timeframe,
                        execution_id=execution_id,
                        request_id=request_id,
                    )
                    if attempts_used >= max_retry_attempts or not retryable:
                        raise
            else:
                raise RuntimeError(last_error or "backtest execution failed without explicit error")
        return {
            "status": "completed",
            "request_id": request_id,
            "execution_id": execution_id,
            "run_id": run_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "bars_processed": payload["bars_processed"],
            "metrics": payload["metrics"],
            "recovered_executions": recovered_executions,
            "attempts_used": attempts_used,
            "retry_count": max(attempts_used - 1, 0),
            "execution": self.recent_backtest_executions(limit=1)["executions"][0],
        }

    def recent_backtest_runs(self, limit: int = 10) -> dict[str, object]:
        """查询最近几次已持久化的回测结果。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"runs": repository.fetch_recent_runs(limit=limit)}

    def recent_backtest_executions(self, limit: int = 10) -> dict[str, object]:
        """查询最近几次“尝试执行回测”的记录，包括失败和中断。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"executions": repository.fetch_recent_executions(limit=limit)}

    def recent_execution_requests(self, limit: int = 10) -> dict[str, object]:
        """查询最近几条 request 级 execution 链。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"requests": repository.fetch_recent_execution_requests(limit=limit)}

    def execution_detail(self, execution_id: str) -> dict[str, object]:
        """查询某次执行尝试的完整详情。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"detail": repository.fetch_execution_detail(execution_id=execution_id)}

    def execution_request_detail(self, request_id: str) -> dict[str, object]:
        """查询某次 request 级执行链的完整详情。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"detail": repository.fetch_execution_request_detail(request_id=request_id)}

    def protection_status(self, symbol: str, timeframe: str = "1d") -> dict[str, object]:
        """查询某个标的/周期当前是否处于保护模式，以及冷却窗口是否仍在生效。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"protection": repository.fetch_protection_status(symbol=symbol, timeframe=timeframe)}

    def backtest_run_detail(self, run_id: str) -> dict[str, object]:
        """查询某次回测的完整明细。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            detail = repository.fetch_run_detail(run_id)
            return {"detail": detail}

    def recent_order_events(self, limit: int = 20) -> dict[str, object]:
        """查询最近的订单事件，用于快速排查最近发生了什么。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"orders": repository.fetch_recent_order_events(limit=limit)}

    def order_detail(self, order_id: str) -> dict[str, object]:
        """查询某一笔订单从创建到结束的完整生命周期。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"detail": repository.fetch_order_detail(order_id=order_id)}

    def recent_audit_events(self, limit: int = 20) -> dict[str, object]:
        """查询最近的审计日志，便于查看策略和风控为何这么决定。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"audit_events": repository.fetch_recent_audit_events(limit=limit)}

    def recent_notification_events(self, limit: int = 20) -> dict[str, object]:
        """查询最近通知事件，确认哪些关键运行事件已被提升成告警。"""
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"notifications": repository.fetch_recent_notification_events(limit=limit)}

    def recent_live_cycles(self, limit: int = 20) -> dict[str, object]:
        """查询最近的 live runner 周期。"""
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"live_cycles": repository.fetch_recent_live_cycles(limit=limit)}

    def live_runner_status(self, limit: int = 20) -> dict[str, object]:
        """查看 live runner 汇总状态。"""
        history_payload = self.dashboard_history(runs_limit=5, events_limit=limit)
        return {"summary": history_payload["live_runner_summary"]}

    def live_cycle_detail(self, cycle_id: str) -> dict[str, object]:
        """查看单个 live cycle 的完整详情。"""
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"cycle": repository.fetch_live_cycle_detail(cycle_id=cycle_id)}

    def live_run_cycle(
        self,
        *,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
        runner_id: str = "",
    ) -> dict[str, object]:
        """执行一次 live runner 周期。

        当前阶段的 live runner 仍然基于本地历史数据，但它已经具备了
        “轮询周期”的基本语义：
        1. 先看最新 bar 水位；
        2. 如果没有新数据，就显式记一次 skipped cycle；
        3. 如果有新数据，就走完整持久化回测，并把 request/execution/run 串回这个周期。
        """
        effective_runner_id = self._effective_live_runner_id(runner_id)
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            bar_repository = BarRepository(self.settings.data.duckdb_path)
            latest_bar = bar_repository.fetch_latest_bar_summary(symbol=symbol, timeframe=timeframe)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            previous_cycle = repository.fetch_latest_live_cycle_watermark(
                runner_id=effective_runner_id,
                symbol=symbol,
                timeframe=timeframe,
            )
            cycle_id = repository.create_live_cycle(
                runner_id=effective_runner_id,
                symbol=symbol,
                timeframe=timeframe,
                initial_equity=initial_equity,
                latest_bar_at=str(latest_bar.get("latest_bar_at", "")),
                processed_bar_count=int(latest_bar.get("bar_count", 0)),
            )

        latest_bar_at = str(latest_bar.get("latest_bar_at", ""))
        bar_count = int(latest_bar.get("bar_count", 0))
        if not latest_bar_at or bar_count <= 0:
            with database_lock(self.settings.data.duckdb_path):
                repository = BacktestRunRepository(self.settings.data.duckdb_path)
                repository.finish_live_cycle(
                    cycle_id=cycle_id,
                    status="skipped",
                    latest_bar_at=latest_bar_at,
                    processed_bar_count=bar_count,
                    skip_reason="no_data",
                    cycle_note="live cycle skipped because no bars were available",
                )
                detail = repository.fetch_live_cycle_detail(cycle_id=cycle_id)
            return {"status": "skipped", "cycle": detail, "runner_id": effective_runner_id}

        previous_bar_at = str(previous_cycle.get("latest_bar_at", "")) if previous_cycle else ""
        if previous_bar_at and previous_bar_at == latest_bar_at:
            with database_lock(self.settings.data.duckdb_path):
                repository = BacktestRunRepository(self.settings.data.duckdb_path)
                repository.finish_live_cycle(
                    cycle_id=cycle_id,
                    status="skipped",
                    latest_bar_at=latest_bar_at,
                    processed_bar_count=bar_count,
                    skip_reason="no_new_data",
                    cycle_note="live cycle skipped because market watermark did not advance",
                )
                detail = repository.fetch_live_cycle_detail(cycle_id=cycle_id)
            return {"status": "skipped", "cycle": detail, "runner_id": effective_runner_id}

        try:
            persisted = self.persist_backtest_run(
                symbol=symbol,
                timeframe=timeframe,
                initial_equity=initial_equity,
            )
        except Exception as exc:
            with database_lock(self.settings.data.duckdb_path):
                repository = BacktestRunRepository(self.settings.data.duckdb_path)
                repository.finish_live_cycle(
                    cycle_id=cycle_id,
                    status="failed",
                    latest_bar_at=latest_bar_at,
                    processed_bar_count=bar_count,
                    error_message=str(exc),
                    protection_mode=False,
                    cycle_note="live cycle failed before a persisted run could complete",
                )
                detail = repository.fetch_live_cycle_detail(cycle_id=cycle_id)
            self._record_notification(
                severity="error",
                category="live_cycle_failed",
                title="Live cycle failed",
                message=str(exc),
                symbol=symbol,
                timeframe=timeframe,
            )
            return {"status": "failed", "cycle": detail, "runner_id": effective_runner_id}

        execution_payload = persisted.get("execution") or {}
        final_status = str(persisted.get("status", "completed"))
        cycle_status = "completed" if final_status == "completed" else "blocked" if final_status == "blocked" else "failed"
        skip_reason = "protection_mode" if cycle_status == "blocked" else ""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            repository.finish_live_cycle(
                cycle_id=cycle_id,
                status=cycle_status,
                latest_bar_at=latest_bar_at,
                processed_bar_count=bar_count,
                request_id=str(persisted.get("request_id", "")),
                execution_id=str(persisted.get("execution_id", "")),
                run_id=str(persisted.get("run_id") or ""),
                skip_reason=skip_reason,
                error_message=str(persisted.get("message", "")) if cycle_status != "completed" else "",
                protection_mode=bool(execution_payload.get("protection_mode")),
                cycle_note=f"live cycle ended with persisted status {final_status}",
            )
            detail = repository.fetch_live_cycle_detail(cycle_id=cycle_id)
        return {
            "status": cycle_status,
            "runner_id": effective_runner_id,
            "cycle": detail,
            "persisted_run": persisted,
        }

    def run_live_runner(
        self,
        *,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
        runner_id: str = "",
        cycles: int | None = None,
    ) -> dict[str, object]:
        """按配置或调用参数连续执行多轮 live cycle。

        当前这还不是后台 daemon，而是一个“可重复执行的前台 runner skeleton”。
        但它已经把轮询间隔、runner_id 和周期结果列表这些长期运行需要的基本概念补齐了。
        """
        effective_runner_id = self._effective_live_runner_id(runner_id)
        cycle_limit = max(int(cycles or self.settings.live.max_cycles_per_run), 1)
        poll_interval_seconds = max(float(self.settings.live.poll_interval_seconds), 0.0)
        results: list[dict[str, object]] = []
        for index in range(cycle_limit):
            results.append(
                self.live_run_cycle(
                    symbol=symbol,
                    timeframe=timeframe,
                    initial_equity=initial_equity,
                    runner_id=effective_runner_id,
                )
            )
            if index < cycle_limit - 1 and poll_interval_seconds > 0:
                time.sleep(poll_interval_seconds)
        return {
            "runner_id": effective_runner_id,
            "cycles_requested": cycle_limit,
            "poll_interval_seconds": poll_interval_seconds,
            "results": results,
        }

    def notification_summary(self, limit: int = 50) -> dict[str, object]:
        """汇总最近通知事件，方便快速看近况而不是逐条翻告警。"""
        history_payload = self.dashboard_history(runs_limit=5, events_limit=limit)
        return {"summary": history_payload["notification_summary"]}

    def notification_owner_summary(self, limit: int = 50) -> dict[str, object]:
        """按负责人汇总最近通知事件，方便看 owner 当前负载。"""
        history_payload = self.dashboard_history(runs_limit=5, events_limit=limit)
        return {"summary": history_payload["notification_owner_summary"]}

    def notification_sla_summary(self, limit: int = 50) -> dict[str, object]:
        """汇总已分派但仍未确认且超过 SLA 的通知。"""
        history_payload = self.dashboard_history(runs_limit=5, events_limit=limit)
        return {"summary": history_payload["notification_sla_summary"]}

    def notification_inbox(self, limit: int = 50) -> dict[str, object]:
        """查看当前仍在活跃队列中的通知。"""
        history_payload = self.dashboard_history(runs_limit=5, events_limit=limit)
        return {"inbox": history_payload["notification_inbox"]}

    def acknowledge_notification(self, event_id: str, note: str = "") -> dict[str, object]:
        """确认某条通知已经被人查看或处理过。"""
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            repository.acknowledge_notification_event(event_id=event_id, note=note)
            refreshed = repository.fetch_recent_notification_events(limit=200)
        matched = next((item for item in refreshed if item.get("event_id") == event_id), None)
        return {"notification": matched}

    def batch_acknowledge_notifications(self, event_ids: list[str], note: str = "") -> dict[str, object]:
        """批量确认多条通知。"""
        normalized = [item.strip() for item in event_ids if item.strip()]
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            for event_id in normalized:
                repository.acknowledge_notification_event(event_id=event_id, note=note)
            refreshed = repository.fetch_recent_notification_events(limit=500)
        return {
            "processed": len(normalized),
            "notifications": self._match_notifications_by_event_ids(normalized, refreshed),
        }

    def assign_notification(self, event_id: str, owner: str, note: str = "") -> dict[str, object]:
        """给某条通知指定后续负责人。"""
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            repository.assign_notification_event(event_id=event_id, owner=owner, note=note)
            refreshed = repository.fetch_recent_notification_events(limit=200)
        matched = next((item for item in refreshed if item.get("event_id") == event_id), None)
        return {"notification": matched}

    def batch_assign_notifications(self, event_ids: list[str], owner: str, note: str = "") -> dict[str, object]:
        """批量给通知指定负责人。"""
        normalized = [item.strip() for item in event_ids if item.strip()]
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            for event_id in normalized:
                repository.assign_notification_event(event_id=event_id, owner=owner, note=note)
            refreshed = repository.fetch_recent_notification_events(limit=500)
        return {
            "processed": len(normalized),
            "owner": owner,
            "notifications": self._match_notifications_by_event_ids(normalized, refreshed),
        }

    def resolve_notification(self, event_id: str, note: str = "") -> dict[str, object]:
        """把某条通知标记为已经处理完成。"""
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            repository.resolve_notification_event(event_id=event_id, note=note)
            refreshed = repository.fetch_recent_notification_events(limit=200)
        matched = next((item for item in refreshed if item.get("event_id") == event_id), None)
        return {"notification": matched}

    def batch_resolve_notifications(self, event_ids: list[str], note: str = "") -> dict[str, object]:
        """批量把通知标记为已解决。"""
        normalized = [item.strip() for item in event_ids if item.strip()]
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            for event_id in normalized:
                repository.resolve_notification_event(event_id=event_id, note=note)
            refreshed = repository.fetch_recent_notification_events(limit=500)
        return {
            "processed": len(normalized),
            "notifications": self._match_notifications_by_event_ids(normalized, refreshed),
        }

    def reopen_notification(self, event_id: str, note: str = "") -> dict[str, object]:
        """把已解决通知重新放回活跃队列。"""
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            repository.reopen_notification_event(
                event_id=event_id,
                note=note,
                reset_acknowledgement=bool(self.settings.notification.reopen_resets_acknowledgement),
            )
            refreshed = repository.fetch_recent_notification_events(limit=200)
        matched = next((item for item in refreshed if item.get("event_id") == event_id), None)
        return {"notification": matched}

    def batch_reopen_notifications(self, event_ids: list[str], note: str = "") -> dict[str, object]:
        """批量把已解决通知重新放回活跃队列。"""
        normalized = [item.strip() for item in event_ids if item.strip()]
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            for event_id in normalized:
                repository.reopen_notification_event(
                    event_id=event_id,
                    note=note,
                    reset_acknowledgement=bool(self.settings.notification.reopen_resets_acknowledgement),
                )
            refreshed = repository.fetch_recent_notification_events(limit=500)
        return {
            "processed": len(normalized),
            "notifications": self._match_notifications_by_event_ids(normalized, refreshed),
        }

    def escalate_notifications(self, limit: int = 50) -> dict[str, object]:
        """把长时间未确认的高优先级通知标记成已升级。"""
        escalation_window_seconds = max(int(self.settings.notification.escalation_window_seconds), 0)
        if escalation_window_seconds <= 0:
            return {
                "processed": 0,
                "escalated": 0,
                "window_seconds": escalation_window_seconds,
                "message": "notification escalation is disabled",
            }

        candidates = self.recent_notification_events(limit=limit)["notifications"]
        now = datetime.now(timezone.utc)
        processed = 0
        escalated = 0

        for event in candidates:
            processed += 1
            if str(event.get("acknowledged_at", "")).strip():
                continue
            if str(event.get("escalated_at", "")).strip():
                continue
            if not self._notification_meets_escalation_threshold(str(event.get("severity", ""))):
                continue
            timestamp_text = str(event.get("timestamp", "")).strip()
            if not timestamp_text:
                continue
            try:
                created_at = datetime.fromisoformat(timestamp_text)
            except ValueError:
                continue
            age_seconds = (now - created_at).total_seconds()
            if age_seconds < escalation_window_seconds:
                continue

            reason = (
                f"unacknowledged for {int(age_seconds)} seconds; "
                f"threshold={escalation_window_seconds}s severity={event.get('severity', '')}"
            )
            with database_lock(self.settings.data.duckdb_path):
                create_schema(self.settings.data.duckdb_path)
                repository = BacktestRunRepository(self.settings.data.duckdb_path)
                repository.mark_notification_escalated(
                    event_id=str(event.get("event_id", "")),
                    escalation_level="stale_unacknowledged",
                    escalation_reason=reason,
                )
            escalated += 1

        return {
            "processed": processed,
            "escalated": escalated,
            "window_seconds": escalation_window_seconds,
            "min_severity": self.settings.notification.escalation_min_severity,
        }

    def deliver_notifications(self, limit: int = 20) -> dict[str, object]:
        """让通知 worker 处理待投递事件。

        注意这里的“deliver”在当前阶段表示：
        - worker 已经读取 queued 事件；
        - 尝试把它交给本地 adapter 骨架；
        - 再把尝试结果回写到数据库。

        这样一来，后续哪怕换成真实 Telegram/微信 provider，
        也只需要替换 adapter，而不用回头修改业务侧的通知生成逻辑。
        """
        self._maybe_reconcile_runtime_state()
        max_delivery_attempts = max(int(self.settings.notification.max_delivery_attempts), 1)
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            candidates = repository.fetch_notifications_pending_delivery(
                limit=limit,
                max_delivery_attempts=max_delivery_attempts,
            )

        processed = 0
        dispatched = 0
        failed_retryable = 0
        failed_final = 0

        for event in candidates:
            processed += 1
            attempt_number = int(event.get("delivery_attempts", 0)) + 1
            event_id = str(event.get("event_id", ""))
            LOGGER.info(
                "dispatching notification event_id=%s provider=%s attempt=%s/%s previous_status=%s",
                event_id,
                event.get("provider", ""),
                attempt_number,
                max_delivery_attempts,
                event.get("delivery_status", ""),
            )
            try:
                delivery_target = dispatch_notification_via_adapter(self.settings.notification, event)
                with database_lock(self.settings.data.duckdb_path):
                    repository = BacktestRunRepository(self.settings.data.duckdb_path)
                    repository.mark_notification_delivery_result(
                        event_id=event_id,
                        delivery_status="dispatched",
                        delivery_target=delivery_target,
                        delivered_at=datetime.now(timezone.utc).isoformat(),
                        last_error="",
                        next_delivery_attempt_at="",
                        increment_attempts=True,
                    )
                dispatched += 1
            except Exception as exc:
                last_error = str(exc)
                next_status = (
                    "delivery_failed_final"
                    if attempt_number >= max_delivery_attempts
                    else "delivery_failed_retryable"
                )
                retry_backoff_seconds = self._compute_notification_delivery_backoff_seconds(attempt_number)
                next_delivery_attempt_at = ""
                if next_status == "delivery_failed_retryable":
                    next_delivery_attempt_at = (
                        datetime.now(timezone.utc) + timedelta(seconds=retry_backoff_seconds)
                    ).isoformat()
                with database_lock(self.settings.data.duckdb_path):
                    repository = BacktestRunRepository(self.settings.data.duckdb_path)
                    repository.mark_notification_delivery_result(
                        event_id=event_id,
                        delivery_status=next_status,
                        delivery_target=str(event.get("delivery_target", "")),
                        delivered_at="",
                        last_error=last_error,
                        next_delivery_attempt_at=next_delivery_attempt_at,
                        increment_attempts=True,
                    )
                if next_status == "delivery_failed_final":
                    failed_final += 1
                    LOGGER.error(
                        "notification delivery reached final failure event_id=%s provider=%s attempt=%s/%s reason=%s",
                        event_id,
                        event.get("provider", ""),
                        attempt_number,
                        max_delivery_attempts,
                        last_error,
                    )
                else:
                    failed_retryable += 1
                    LOGGER.warning(
                        "notification delivery failed but remains retryable event_id=%s provider=%s attempt=%s/%s backoff_seconds=%.3f next_delivery_attempt_at=%s reason=%s",
                        event_id,
                        event.get("provider", ""),
                        attempt_number,
                        max_delivery_attempts,
                        retry_backoff_seconds,
                        next_delivery_attempt_at,
                        last_error,
                    )

        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            remaining_pending = len(
                repository.fetch_notifications_pending_delivery(
                    limit=1000,
                    max_delivery_attempts=max_delivery_attempts,
                )
            )

        return {
            "processed": processed,
            "dispatched": dispatched,
            "failed_retryable": failed_retryable,
            "failed_final": failed_final,
            "remaining_pending": remaining_pending,
            "max_delivery_attempts": max_delivery_attempts,
        }

    def dashboard_history(self, runs_limit: int = 20, events_limit: int = 20) -> dict[str, object]:
        """把历史数据整理成前端更容易消费的结构。"""
        with database_lock(self.settings.data.duckdb_path):
            create_schema(self.settings.data.duckdb_path)
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            bundle = repository.fetch_history_bundle(runs_limit=runs_limit, events_limit=events_limit)
            runtime_reconcile_preview = {
                "repaired_assignment_timestamps": repository.count_notification_assignment_backfill_candidates(),
                "repaired_resolution_acknowledgements": repository.count_notification_resolution_ack_backfill_candidates(),
                "recovered_stale_executions": repository.count_stale_executions(),
            }
            return build_history_payload(
                bundle["runs"],
                bundle["executions"],
                bundle["live_cycles"],
                bundle["orders"],
                bundle["audit_events"],
                bundle["notification_events"],
                notification_assignment_sla_seconds=self.settings.notification.assignment_sla_seconds,
                notification_assignment_sla_overrides=self._notification_assignment_sla_overrides(),
                runtime_reconcile_preview=runtime_reconcile_preview,
            )

    def controller_health(self, runs_limit: int = 20, events_limit: int = 50) -> dict[str, object]:
        """输出控制器当前最值得优先排查的健康视图。"""
        history_payload = self.dashboard_history(runs_limit=runs_limit, events_limit=events_limit)
        return {"controller_health": history_payload["controller_health"]}

    def export_backtest(
        self,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
        output_path: str = "var/reports/backtest.json",
    ) -> dict[str, object]:
        """导出回测 JSON 报告，适合给脚本或其它工具继续消费。"""
        payload = self.backtest_symbol(symbol=symbol, timeframe=timeframe, initial_equity=initial_equity)
        written_path = export_backtest_result(payload, output_path)
        return {
            "output_path": written_path,
            "symbol": symbol,
            "bars_processed": payload["bars_processed"],
            "metrics": payload["metrics"],
        }

    def dashboard_snapshot(
        self,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
    ) -> dict[str, object]:
        """生成单次回测的 dashboard 数据快照。"""
        backtest_payload = self.backtest_symbol(symbol=symbol, timeframe=timeframe, initial_equity=initial_equity)
        return build_dashboard_payload(
            backtest_payload,
            symbol=symbol,
            timeframe=timeframe,
            initial_equity=initial_equity,
            settings={
                "strategy": asdict(self.settings.strategy),
                "risk": asdict(self.settings.risk),
                "execution": asdict(self.settings.execution),
            },
        )

    def export_dashboard_snapshot(
        self,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
        output_path: str = "var/reports/dashboard.json",
    ) -> dict[str, object]:
        """导出 dashboard 用的 JSON 数据。"""
        payload = self.dashboard_snapshot(symbol=symbol, timeframe=timeframe, initial_equity=initial_equity)
        written_path = export_backtest_result(payload, output_path)
        return {
            "output_path": written_path,
            "symbol": symbol,
            "summary_cards": len(payload["summary_cards"]),
            "recent_trades": len(payload["recent_trades"]),
        }

    def export_dashboard_html(
        self,
        symbol: str,
        timeframe: str = "1d",
        initial_equity: float = 100_000.0,
        output_path: str = "var/reports/dashboard.html",
    ) -> dict[str, object]:
        """导出单次回测的静态 HTML 看板。"""
        payload = self.dashboard_snapshot(symbol=symbol, timeframe=timeframe, initial_equity=initial_equity)
        written_path = render_dashboard_html(payload, output_path)
        return {
            "output_path": written_path,
            "symbol": symbol,
            "summary_cards": len(payload["summary_cards"]),
            "recent_trades": len(payload["recent_trades"]),
        }

    def export_history_html(
        self,
        runs_limit: int = 20,
        events_limit: int = 20,
        output_path: str = "var/reports/history.html",
    ) -> dict[str, object]:
        """导出历史回测的静态 HTML 页面。"""
        payload = self.dashboard_history(runs_limit=runs_limit, events_limit=events_limit)
        written_path = render_history_html(payload, output_path)
        return {
            "output_path": written_path,
            "runs": len(payload["runs_table"]),
            "executions": len(payload["recent_executions"]),
            "orders": len(payload["recent_orders"]),
            "audit_events": len(payload["recent_audit_events"]),
            "notifications": len(payload["recent_notifications"]),
        }
