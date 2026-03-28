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
from datetime import datetime, timezone
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
from quanttrade.notification.service import append_notification_to_outbox, should_emit_notification
from quanttrade.risk.engine import RiskEngine
from quanttrade.strategies.atr_dtf import AtrDynamicTrendFollowingStrategy

LOGGER = logging.getLogger(__name__)


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

    def _classify_execution_error(self, exc: Exception) -> dict[str, object]:
        """把一次执行异常翻译成运行控制器可理解的决策信息。

        这一步很关键，因为运行控制器真正需要的不是“异常字符串”，而是：
        1. 这类错误是否值得再试；
        2. 如果不再试，是因为输入有问题，还是因为系统主动阻断；
        3. 日志和持久化里应该如何描述这次判断。
        """
        if isinstance(exc, RetryableExecutionError):
            return {
                "retryable": True,
                "failure_class": exc.__class__.__name__,
                "log_reason": str(exc),
            }
        if isinstance(exc, NonRetryableExecutionError):
            return {
                "retryable": False,
                "failure_class": exc.__class__.__name__,
                "log_reason": str(exc),
            }
        return {
            "retryable": False,
            "failure_class": exc.__class__.__name__,
            "log_reason": str(exc),
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
        if self.settings.notification.enabled and should_emit_notification(self.settings.notification, severity):
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
            }
            delivery_target = append_notification_to_outbox(self.settings.notification, outbox_payload)
            delivery_status = "queued"
        elif self.settings.notification.enabled:
            delivery_status = "filtered"

        with database_lock(self.settings.data.duckdb_path):
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
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            return {"notifications": repository.fetch_recent_notification_events(limit=limit)}

    def dashboard_history(self, runs_limit: int = 20, events_limit: int = 20) -> dict[str, object]:
        """把历史数据整理成前端更容易消费的结构。"""
        with database_lock(self.settings.data.duckdb_path):
            repository = BacktestRunRepository(self.settings.data.duckdb_path)
            bundle = repository.fetch_history_bundle(runs_limit=runs_limit, events_limit=events_limit)
            return build_history_payload(
                bundle["runs"],
                bundle["executions"],
                bundle["orders"],
                bundle["audit_events"],
                bundle["notification_events"],
            )

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
