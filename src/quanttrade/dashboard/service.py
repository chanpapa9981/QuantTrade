"""Dashboard 数据整理层。

这个模块不负责画页面，而是负责把原始回测/历史数据重新整理成前端更容易消费的结构。
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

_NOTIFICATION_SEVERITY_PRIORITY = {
    "critical": 4,
    "error": 3,
    "warning": 2,
    "info": 1,
}


def _format_config_sections(
    settings: dict[str, dict[str, object]],
    symbol: str,
    timeframe: str,
    initial_equity: float,
) -> list[dict[str, object]]:
    """把配置拆成页面上更容易阅读的参数面板结构。"""
    strategy = settings.get("strategy", {})
    risk = settings.get("risk", {})
    execution = settings.get("execution", {})
    return [
        {
            "id": "market-context",
            "title": "Market Context",
            "items": [
                {"label": "symbol", "value": symbol},
                {"label": "timeframe", "value": timeframe},
                {"label": "initial_equity", "value": initial_equity},
                {"label": "strategy_name", "value": strategy.get("name", "")},
            ],
        },
        {
            "id": "strategy",
            "title": "Strategy Parameters",
            "items": [
                {"label": "entry_donchian_n", "value": strategy.get("entry_donchian_n", 0)},
                {"label": "exit_donchian_m", "value": strategy.get("exit_donchian_m", 0)},
                {"label": "atr_smooth_period", "value": strategy.get("atr_smooth_period", 0)},
                {"label": "risk_coefficient_k", "value": strategy.get("risk_coefficient_k", 0.0)},
                {"label": "adx_trend_filter", "value": strategy.get("adx_trend_filter", 0.0)},
                {"label": "risk_pct", "value": strategy.get("risk_pct", 0.0)},
                {"label": "max_symbol_weight", "value": strategy.get("max_symbol_weight", 0.0)},
            ],
        },
        {
            "id": "risk",
            "title": "Risk Controls",
            "items": [
                {"label": "max_daily_drawdown", "value": risk.get("max_daily_drawdown", 0.0)},
                {"label": "global_max_exposure", "value": risk.get("global_max_exposure", 0.0)},
                {"label": "max_open_positions", "value": risk.get("max_open_positions", 0)},
                {"label": "slippage_tolerance", "value": risk.get("slippage_tolerance", 0.0)},
                {"label": "liquidity_filter", "value": risk.get("liquidity_filter", 0.0)},
            ],
        },
        {
            "id": "execution",
            "title": "Execution Controls",
            "items": [
                {"label": "commission_per_order", "value": execution.get("commission_per_order", 0.0)},
                {"label": "commission_per_share", "value": execution.get("commission_per_share", 0.0)},
                {"label": "min_commission", "value": execution.get("min_commission", 0.0)},
                {"label": "simulated_slippage_bps", "value": execution.get("simulated_slippage_bps", 0.0)},
                {"label": "max_fill_ratio_per_bar", "value": execution.get("max_fill_ratio_per_bar", 0.0)},
                {"label": "open_order_timeout_bars", "value": execution.get("open_order_timeout_bars", 0)},
                {"label": "max_retry_attempts", "value": execution.get("max_retry_attempts", 0)},
                {"label": "protection_mode_failure_threshold", "value": execution.get("protection_mode_failure_threshold", 0)},
                {"label": "protection_mode_cooldown_seconds", "value": execution.get("protection_mode_cooldown_seconds", 0)},
                {
                    "label": "skip_run_on_protection_mode",
                    "value": execution.get("skip_run_on_protection_mode", False),
                },
            ],
        },
    ]


def _build_order_lifecycles(orders: list[dict[str, object]]) -> list[dict[str, object]]:
    """把订单事件按 `order_id` 归并成历史页使用的生命周期摘要。"""
    grouped: dict[str, list[dict[str, object]]] = {}
    for order in orders:
        order_id = str(order.get("order_id", ""))
        grouped.setdefault(order_id, []).append(order)

    lifecycles: list[dict[str, object]] = []
    for order_id, events in grouped.items():
        if not order_id:
            continue
        # 这里的 orders 输入通常是按时间倒序排列，所以：
        # - 最后一个事件反而是“最早发生”的；
        # - 第一个事件反而是“最新状态”。
        first = events[-1]
        last = events[0]
        status_path = [str(event.get("status", "")) for event in reversed(events)]
        broker_status_path = [str(event.get("broker_status", "")) for event in reversed(events)]
        lifecycles.append(
            {
                "order_id": order_id,
                "run_id": last.get("run_id", ""),
                "side": last.get("side", ""),
                "submitted_at": first.get("timestamp", ""),
                "last_updated_at": last.get("timestamp", ""),
                "final_status": last.get("status", ""),
                "latest_broker_status": last.get("broker_status", ""),
                "latest_status_detail": last.get("status_detail", ""),
                "status_path": " -> ".join(status_path),
                "broker_status_path": " -> ".join(broker_status_path),
                "requested_quantity": first.get("quantity", 0),
                "filled_quantity": max(int(event.get("filled_quantity", 0)) for event in events),
                "remaining_quantity": last.get("remaining_quantity", 0),
            }
        )
    lifecycles.sort(key=lambda item: str(item.get("last_updated_at", "")), reverse=True)
    return lifecycles


def _build_order_lifecycle_details(orders: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    """把订单事件按 `order_id` 聚合成明细字典，供前端点击联动时直接读取。"""
    grouped: dict[str, list[dict[str, object]]] = {}
    for order in orders:
        order_id = str(order.get("order_id", ""))
        if not order_id:
            continue
        grouped.setdefault(order_id, []).append(order)
    for events in grouped.values():
        events.sort(key=lambda item: str(item.get("timestamp", "")))
    return grouped


def _build_notification_summary(notification_events: list[dict[str, object]]) -> list[dict[str, object]]:
    """把通知事件压缩成更适合值班视角的聚合表。

    原始通知表更适合追单条事件；
    这个聚合表更适合快速回答：
    - 最近最常见的告警类别是什么；
    - 哪种状态最常出现；
    - 哪类告警被静默压缩得最多。
    """
    grouped: dict[tuple[str, str, str], dict[str, object]] = {}
    for event in notification_events:
        key = (
            str(event.get("category", "")),
            str(event.get("severity", "")),
            str(event.get("delivery_status", "")),
        )
        current = grouped.setdefault(
            key,
            {
                "category": key[0],
                "severity": key[1],
                "delivery_status": key[2],
                "event_count": 0,
                "suppressed_duplicates": 0,
                "last_seen_at": "",
            },
        )
        current["event_count"] = int(current.get("event_count", 0)) + 1
        current["suppressed_duplicates"] = int(current.get("suppressed_duplicates", 0)) + int(
            event.get("suppressed_duplicate_count", 0)
        )
        if str(event.get("timestamp", "")) > str(current.get("last_seen_at", "")):
            current["last_seen_at"] = str(event.get("timestamp", ""))
    rows = list(grouped.values())
    rows.sort(
        key=lambda item: (
            -int(item.get("event_count", 0)),
            -int(item.get("suppressed_duplicates", 0)),
            str(item.get("category", "")),
        )
    )
    return rows


def _build_notification_owner_summary(notification_events: list[dict[str, object]]) -> list[dict[str, object]]:
    """按负责人归并通知事件，帮助快速看 owner 负载。"""
    grouped: dict[str, dict[str, object]] = {}
    for event in notification_events:
        owner = str(event.get("assigned_to", "")).strip() or "(unassigned)"
        current = grouped.setdefault(
            owner,
            {
                "owner": owner,
                "event_count": 0,
                "active_count": 0,
                "resolved_count": 0,
                "reopened_count": 0,
                "unacknowledged_count": 0,
                "escalated_count": 0,
                "open_high_priority_count": 0,
                "last_seen_at": "",
            },
        )
        current["event_count"] = int(current.get("event_count", 0)) + 1
        resolved = bool(str(event.get("resolved_at", "")).strip())
        if int(event.get("reopen_count", 0)) > 0:
            current["reopened_count"] = int(current.get("reopened_count", 0)) + 1
        if resolved:
            current["resolved_count"] = int(current.get("resolved_count", 0)) + 1
        else:
            current["active_count"] = int(current.get("active_count", 0)) + 1
        if not resolved and not str(event.get("acknowledged_at", "")).strip():
            current["unacknowledged_count"] = int(current.get("unacknowledged_count", 0)) + 1
        if not resolved and str(event.get("escalated_at", "")).strip():
            current["escalated_count"] = int(current.get("escalated_count", 0)) + 1
        if (
            not resolved
            and not str(event.get("acknowledged_at", "")).strip()
            and str(event.get("severity", "")).strip() in {"error", "critical"}
        ):
            current["open_high_priority_count"] = int(current.get("open_high_priority_count", 0)) + 1
        if str(event.get("timestamp", "")) > str(current.get("last_seen_at", "")):
            current["last_seen_at"] = str(event.get("timestamp", ""))
    rows = list(grouped.values())
    rows.sort(
        key=lambda item: (
            -int(item.get("unacknowledged_count", 0)),
            -int(item.get("escalated_count", 0)),
            -int(item.get("event_count", 0)),
            str(item.get("owner", "")),
        )
    )
    return rows


def _build_notification_inbox(notification_events: list[dict[str, object]]) -> list[dict[str, object]]:
    """把活跃通知整理成更接近日常值班的 inbox 视图。"""
    now = datetime.now(UTC)
    rows: list[dict[str, object]] = []
    for event in notification_events:
        if str(event.get("resolved_at", "")).strip():
            continue
        anchor_text = str(event.get("reopened_at", "")).strip() or str(event.get("timestamp", "")).strip()
        if not anchor_text:
            continue
        try:
            anchor_at = datetime.fromisoformat(anchor_text)
        except ValueError:
            continue
        severity = str(event.get("severity", "")).strip().lower()
        age_seconds = int((now - anchor_at).total_seconds())
        rows.append(
            {
                "event_id": str(event.get("event_id", "")),
                "owner": str(event.get("assigned_to", "")).strip() or "(unassigned)",
                "severity": str(event.get("severity", "")),
                "category": str(event.get("category", "")),
                "title": str(event.get("title", "")),
                "delivery_status": str(event.get("delivery_status", "")),
                "active_since": anchor_text,
                "age_seconds": age_seconds,
                "ack_state": "acked" if str(event.get("acknowledged_at", "")).strip() else "unacked",
                "escalated": bool(str(event.get("escalated_at", "")).strip()),
                "reopened": int(event.get("reopen_count", 0)) > 0,
                "reopen_count": int(event.get("reopen_count", 0)),
                "next_delivery_attempt_at": str(event.get("next_delivery_attempt_at", "")),
            }
        )
    rows.sort(
        key=lambda item: (
            -int(bool(item.get("escalated"))),
            -_NOTIFICATION_SEVERITY_PRIORITY.get(str(item.get("severity", "")).strip().lower(), 0),
            -int(item.get("age_seconds", 0)),
            str(item.get("owner", "")),
        )
    )
    return rows


def _build_controller_health(
    *,
    execution_requests: list[dict[str, object]],
    live_runner_summary: list[dict[str, object]],
    maintenance_runner_summary: list[dict[str, object]],
    broker_health: dict[str, object],
    broker_reconcile: dict[str, object],
    notification_events: list[dict[str, object]],
    notification_sla_summary: list[dict[str, object]],
    runtime_reconcile_preview: dict[str, int] | None = None,
) -> dict[str, object]:
    """把控制器最需要优先关注的健康项压成统一视图。"""
    runtime_reconcile_preview = runtime_reconcile_preview or {}
    unacknowledged_critical = len(
        [
            item
            for item in notification_events
            if item.get("severity") == "critical"
            and not str(item.get("resolved_at", "")).strip()
            and not str(item.get("acknowledged_at", "")).strip()
        ]
    )
    blocked_requests = len([item for item in execution_requests if item.get("blocked")])
    cooldown_requests = len([item for item in execution_requests if item.get("cooldown_active")])
    critical_requests = len([item for item in execution_requests if item.get("health_label") == "critical"])
    watch_requests = len([item for item in execution_requests if item.get("health_label") == "watch"])
    stalled_live_runners = len([item for item in live_runner_summary if item.get("stalled")])
    stalled_maintenance_runners = len([item for item in maintenance_runner_summary if item.get("stalled")])
    stale_broker_snapshot = int(bool(broker_health.get("stale")))
    failed_broker_sync = int(bool(broker_health.get("failed")))
    broker_reconcile_drift = int(broker_reconcile.get("mismatch_count", 0) or 0)
    stale_execution_candidates = int(runtime_reconcile_preview.get("recovered_stale_executions", 0))
    assignment_backfill_candidates = int(runtime_reconcile_preview.get("repaired_assignment_timestamps", 0))
    resolution_backfill_candidates = int(runtime_reconcile_preview.get("repaired_resolution_acknowledgements", 0))
    reconcile_candidates = stale_execution_candidates + assignment_backfill_candidates + resolution_backfill_candidates

    issues: list[dict[str, object]] = []

    def add_issue(*, code: str, severity: str, count: int, detail: str) -> None:
        if count <= 0:
            return
        issues.append(
            {
                "code": code,
                "severity": severity,
                "count": count,
                "detail": detail,
            }
        )

    add_issue(
        code="stalled_live_runner",
        severity="warning",
        count=stalled_live_runners,
        detail="最近一次 live cycle 距今已经超过阈值，runner 可能已经停滞或失联。",
    )
    add_issue(
        code="stalled_maintenance_runner",
        severity="warning",
        count=stalled_maintenance_runners,
        detail="maintenance runner 长时间没有新的维护周期，控制器巡检可能已经停住。",
    )
    add_issue(
        code="failed_broker_sync",
        severity="critical",
        count=failed_broker_sync,
        detail="最近一次 broker 同步失败，外部账户快照可能已经失真。",
    )
    add_issue(
        code="stale_broker_snapshot",
        severity="warning",
        count=stale_broker_snapshot,
        detail="最近一次 broker 快照已超过阈值，继续依赖它做判断存在风险。",
    )
    add_issue(
        code="broker_reconcile_drift",
        severity="warning",
        count=broker_reconcile_drift,
        detail="最新本地运行结果与 broker 快照存在 drift，建议进一步做对账排查。",
    )
    add_issue(
        code="stale_execution_candidates",
        severity="critical",
        count=stale_execution_candidates,
        detail="running execution 残留，需要 reconcile 或启动恢复处理。",
    )
    add_issue(
        code="blocked_requests",
        severity="critical",
        count=blocked_requests,
        detail="有 request 已被保护模式拦截，通常说明需要人工复核失败根因。",
    )
    add_issue(
        code="unacknowledged_critical_notifications",
        severity="critical",
        count=unacknowledged_critical,
        detail="存在 critical 告警仍未确认，应该优先处理。",
    )
    add_issue(
        code="sla_breached_notifications",
        severity="warning",
        count=len(notification_sla_summary),
        detail="已分派但超出 SLA 的告警仍未被确认。",
    )
    add_issue(
        code="cooldown_protected_requests",
        severity="warning",
        count=cooldown_requests,
        detail="保护模式冷却尚未结束，新的执行仍可能被阻断。",
    )
    add_issue(
        code="critical_requests",
        severity="warning",
        count=critical_requests,
        detail="存在 request 链已经进入 critical 健康状态。",
    )
    add_issue(
        code="watch_requests",
        severity="info",
        count=watch_requests,
        detail="存在需要继续观察的 request 链，例如刚重试或刚恢复。",
    )
    add_issue(
        code="runtime_reconcile_candidates",
        severity="info",
        count=reconcile_candidates,
        detail="数据库里还存在可自动修复的不一致状态。",
    )

    severity_rank = {"critical": 3, "warning": 2, "info": 1}
    issues.sort(key=lambda item: (-severity_rank.get(str(item.get("severity", "")), 0), -int(item.get("count", 0)), str(item.get("code", ""))))

    return {
        "summary": {
            "blocked_requests": blocked_requests,
            "cooldown_requests": cooldown_requests,
            "critical_requests": critical_requests,
            "watch_requests": watch_requests,
            "stalled_live_runners": stalled_live_runners,
            "stalled_maintenance_runners": stalled_maintenance_runners,
            "failed_broker_sync": failed_broker_sync,
            "stale_broker_snapshot": stale_broker_snapshot,
            "broker_reconcile_drift": broker_reconcile_drift,
            "unacknowledged_critical_notifications": unacknowledged_critical,
            "sla_breached_notifications": len(notification_sla_summary),
            "stale_execution_candidates": stale_execution_candidates,
            "reconcile_candidates": reconcile_candidates,
        },
        "issues": issues[:8],
    }


def _build_live_runner_summary(
    live_cycles: list[dict[str, object]],
    *,
    stall_threshold_seconds: float = 0.0,
) -> list[dict[str, object]]:
    """按 runner + market 汇总 live cycle，帮助观察轮询器健康度。"""
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for cycle in live_cycles:
        key = (
            str(cycle.get("runner_id", "")).strip(),
            str(cycle.get("symbol", "")).strip(),
            str(cycle.get("timeframe", "")).strip(),
        )
        grouped.setdefault(key, []).append(cycle)

    rows: list[dict[str, object]] = []
    for key, cycles in grouped.items():
        ordered = sorted(cycles, key=lambda item: str(item.get("started_at", "")), reverse=True)
        latest = ordered[0]
        idle_streak = 0
        for cycle in ordered:
            if str(cycle.get("status", "")) == "skipped" and str(cycle.get("skip_reason", "")) == "no_new_data":
                idle_streak += 1
                continue
            break
        last_success_at = next(
            (str(item.get("finished_at", "")) for item in ordered if item.get("status") == "completed"),
            "",
        )
        last_cycle_at = str(latest.get("started_at", ""))
        last_cycle_age_seconds = 0
        if last_cycle_at:
            try:
                last_cycle_age_seconds = max(int((datetime.now(UTC) - datetime.fromisoformat(last_cycle_at)).total_seconds()), 0)
            except ValueError:
                last_cycle_age_seconds = 0
        effective_stall_threshold = max(float(stall_threshold_seconds), 0.0)
        stalled = bool(effective_stall_threshold > 0 and last_cycle_age_seconds > effective_stall_threshold)
        rows.append(
            {
                "runner_id": key[0],
                "symbol": key[1],
                "timeframe": key[2],
                "cycle_count": len(ordered),
                "latest_status": str(latest.get("status", "")),
                "last_cycle_at": last_cycle_at,
                "latest_bar_at": str(latest.get("latest_bar_at", "")),
                "completed_count": len([item for item in ordered if item.get("status") == "completed"]),
                "skipped_count": len([item for item in ordered if item.get("status") == "skipped"]),
                "blocked_count": len([item for item in ordered if item.get("status") == "blocked"]),
                "failed_count": len([item for item in ordered if item.get("status") == "failed"]),
                "protection_hits": len([item for item in ordered if item.get("protection_mode")]),
                "idle_streak": idle_streak,
                "last_success_at": last_success_at,
                "last_cycle_age_seconds": last_cycle_age_seconds,
                "stall_threshold_seconds": effective_stall_threshold,
                "stalled": stalled,
            }
        )
    rows.sort(
        key=lambda item: (
            not bool(item.get("stalled")),
            str(item.get("latest_status", "")) not in {"blocked", "failed"},
            -int(item.get("idle_streak", 0)),
            -int(item.get("cycle_count", 0)),
            str(item.get("last_cycle_at", "")),
        )
    )
    return rows


def _build_maintenance_summary(maintenance_cycles: list[dict[str, object]]) -> dict[str, object]:
    """把维护周期压成顶部摘要。"""
    latest = maintenance_cycles[0] if maintenance_cycles else {}
    return {
        "total_maintenance_cycles": len(maintenance_cycles),
        "failed_maintenance_cycles": len([item for item in maintenance_cycles if item.get("status") == "failed"]),
        "latest_maintenance_status": str(latest.get("status", "")),
        "latest_maintenance_at": str(latest.get("started_at", "")),
    }


def _build_maintenance_runner_summary(
    maintenance_cycles: list[dict[str, object]],
    *,
    stall_threshold_seconds: float = 0.0,
) -> list[dict[str, object]]:
    """按 maintenance runner 聚合维护周期，帮助判断巡检器是不是还在正常跳动。

    live runner 关注的是“策略轮询有没有在跑”；
    maintenance runner 关注的是“运维巡检有没有继续工作”。
    两者都是 runner，但观察维度不同，所以这里单独整理。
    """
    grouped: dict[str, list[dict[str, object]]] = {}
    for cycle in maintenance_cycles:
        runner_id = str(cycle.get("runner_id", "")).strip() or "maintenance-default"
        grouped.setdefault(runner_id, []).append(cycle)

    rows: list[dict[str, object]] = []
    for runner_id, cycles in grouped.items():
        ordered = sorted(cycles, key=lambda item: str(item.get("started_at", "")), reverse=True)
        latest = ordered[0]
        last_cycle_at = str(latest.get("started_at", ""))
        last_cycle_age_seconds = 0
        if last_cycle_at:
            try:
                last_cycle_age_seconds = max(int((datetime.now(UTC) - datetime.fromisoformat(last_cycle_at)).total_seconds()), 0)
            except ValueError:
                last_cycle_age_seconds = 0
        effective_stall_threshold = max(float(stall_threshold_seconds), 0.0)
        stalled = bool(effective_stall_threshold > 0 and last_cycle_age_seconds > effective_stall_threshold)
        last_success_at = next(
            (str(item.get("finished_at", "")) for item in ordered if item.get("status") == "completed"),
            "",
        )
        rows.append(
            {
                "runner_id": runner_id,
                "cycle_count": len(ordered),
                "latest_status": str(latest.get("status", "")),
                "last_cycle_at": last_cycle_at,
                "last_cycle_age_seconds": last_cycle_age_seconds,
                "stall_threshold_seconds": effective_stall_threshold,
                "stalled": stalled,
                "completed_count": len([item for item in ordered if item.get("status") == "completed"]),
                "failed_count": len([item for item in ordered if item.get("status") == "failed"]),
                "running_count": len([item for item in ordered if item.get("status") == "running"]),
                "last_success_at": last_success_at,
                "total_emitted_notifications": sum(int(item.get("emitted_notification_count", 0) or 0) for item in ordered),
                "total_delivered_notifications": sum(int(item.get("delivered_notification_count", 0) or 0) for item in ordered),
                "latest_pending_notifications": int(latest.get("remaining_pending_notifications", 0) or 0),
            }
        )
    rows.sort(
        key=lambda item: (
            not bool(item.get("stalled")),
            str(item.get("latest_status", "")) != "failed",
            -int(item.get("failed_count", 0)),
            -int(item.get("cycle_count", 0)),
            str(item.get("last_cycle_at", "")),
        )
    )
    return rows


def _build_broker_sync_summary(broker_syncs: list[dict[str, object]]) -> dict[str, object]:
    """把券商同步记录压缩成历史页顶部摘要。

    券商同步和 execution/live cycle 不同：
    - execution 关注“策略有没有跑起来”；
    - broker sync 关注“外部账户状态有没有被成功拉回本地”。

    所以这里单独做一个摘要，方便快速回答：
    1. 最近有没有同步成功；
    2. 最近一次账户权益是多少；
    3. 最近一次同步对应多少持仓和订单。
    """
    latest = broker_syncs[0] if broker_syncs else {}
    return {
        "total_broker_syncs": len(broker_syncs),
        "failed_broker_syncs": len([item for item in broker_syncs if item.get("status") == "failed"]),
        "latest_broker_sync_status": str(latest.get("status", "")),
        "latest_broker_provider": str(latest.get("provider", "")),
        "latest_broker_equity": float(latest.get("equity", 0.0) or 0.0),
        "latest_broker_cash": float(latest.get("cash", 0.0) or 0.0),
        "latest_broker_positions": int(latest.get("position_count", 0) or 0),
        "latest_broker_orders": int(latest.get("order_count", 0) or 0),
        "latest_broker_synced_at": str(latest.get("synced_at", "")),
    }


def _build_broker_health(
    broker_syncs: list[dict[str, object]],
    *,
    max_snapshot_age_seconds: int = 0,
) -> dict[str, object]:
    """计算最近一份 broker 快照是否过旧、是否已经失败。"""
    latest = broker_syncs[0] if broker_syncs else {}
    synced_at_text = str(latest.get("synced_at", "")).strip()
    age_seconds = 0
    if synced_at_text:
        try:
            synced_at = datetime.fromisoformat(synced_at_text)
            age_seconds = max(int((datetime.now(UTC) - synced_at).total_seconds()), 0)
        except ValueError:
            age_seconds = 0
    threshold = max(int(max_snapshot_age_seconds), 0)
    latest_status = str(latest.get("status", "")).strip()
    stale = bool(threshold > 0 and synced_at_text and age_seconds > threshold)
    failed = latest_status == "failed"
    return {
        "latest_sync_id": str(latest.get("sync_id", "")),
        "latest_provider": str(latest.get("provider", "")),
        "latest_status": latest_status,
        "latest_synced_at": synced_at_text,
        "latest_runner_id": str(latest.get("runner_id", "")),
        "latest_cycle_id": str(latest.get("cycle_id", "")),
        "snapshot_age_seconds": age_seconds,
        "max_snapshot_age_seconds": threshold,
        "stale": stale,
        "failed": failed,
        "failed_sync_count": len([item for item in broker_syncs if item.get("status") == "failed"]),
        "detail": (
            "no broker sync snapshot has been recorded yet"
            if not broker_syncs
            else "latest broker sync failed"
            if failed
            else "latest broker snapshot is older than configured threshold"
            if stale
            else "broker snapshot is healthy"
        ),
    }


def _build_broker_reconcile(
    latest_run_detail: dict[str, object] | None,
    latest_broker_sync_detail: dict[str, object] | None,
    drift_thresholds: dict[str, float] | None = None,
) -> dict[str, object]:
    """对最新本地运行结果和最新 broker 快照做轻量差异预览。

    这里故意把“原始差异”和“真正越过阈值的差异”分开：
    - 原始差异表示两边数字并不完全一样；
    - 越阈差异表示这已经不是正常抖动，而是值得控制器升级关注的 drift。
    """
    drift_thresholds = drift_thresholds or {}
    if not latest_run_detail or not latest_broker_sync_detail:
        return {
            "status": "unavailable",
            "mismatch_count": 0,
            "latest_run_id": str((latest_run_detail or {}).get("run_id", "")),
            "latest_broker_sync_id": str((latest_broker_sync_detail or {}).get("sync_id", "")),
            "symbol": str((latest_run_detail or {}).get("run", {}).get("symbol", "")),
            "timeframe": str((latest_run_detail or {}).get("run", {}).get("timeframe", "")),
            "rows": [],
            "notes": ["latest run detail or broker sync detail is missing"],
        }

    run_summary = dict(latest_run_detail.get("run", {}))
    local_account = dict(latest_run_detail.get("account_snapshot", {}))
    broker_sync = dict(latest_broker_sync_detail.get("sync", {}))
    local_open_orders = len(
        [item for item in latest_run_detail.get("order_lifecycles", []) if str(item.get("final_status", "")) == "open"]
    )
    broker_open_statuses = {"working", "open", "pending_new", "partially_filled", "accepted"}
    broker_open_orders = len(
        [
            item
            for item in latest_broker_sync_detail.get("orders", [])
            if str(item.get("status", "")).strip().lower() in broker_open_statuses
        ]
    )
    rows = [
        {
            "metric": "equity",
            "local_value": float(local_account.get("equity", 0.0) or 0.0),
            "broker_value": float(broker_sync.get("equity", 0.0) or 0.0),
        },
        {
            "metric": "cash",
            "local_value": float(local_account.get("cash", 0.0) or 0.0),
            "broker_value": float(broker_sync.get("cash", 0.0) or 0.0),
        },
        {
            "metric": "open_positions",
            "local_value": int(local_account.get("open_positions", 0) or 0),
            "broker_value": len(latest_broker_sync_detail.get("positions", [])),
        },
        {
            "metric": "open_orders",
            "local_value": local_open_orders,
            "broker_value": broker_open_orders,
        },
    ]
    mismatches: list[str] = []
    raw_differences: list[str] = []
    for row in rows:
        delta = float(row["broker_value"]) - float(row["local_value"])
        row["delta"] = delta
        threshold = abs(float(drift_thresholds.get(str(row["metric"]), 0.0) or 0.0))
        breached = abs(delta) > threshold if threshold > 0 else abs(delta) > 0
        if abs(delta) > 0:
            raw_differences.append(str(row["metric"]))
        row["threshold"] = threshold
        row["breached"] = breached
        row["status"] = "breached" if breached else "within_threshold" if abs(delta) > 0 else "aligned"
        if breached:
            mismatches.append(str(row["metric"]))
    return {
        "status": "drift" if mismatches else "aligned",
        "mismatch_count": len(mismatches),
        "latest_run_id": str(latest_run_detail.get("run", {}).get("run_id", "")),
        "latest_broker_sync_id": str(broker_sync.get("sync_id", "")),
        "symbol": str(run_summary.get("symbol", "")),
        "timeframe": str(run_summary.get("timeframe", "")),
        "rows": rows,
        "notes": (
            ["local run snapshot and broker snapshot are aligned on the tracked metrics"]
            if not raw_differences
            else [f"raw differences observed but still within configured thresholds: {', '.join(raw_differences)}"]
            if not mismatches
            else [f"drift detected in: {', '.join(mismatches)}"]
        ),
    }


def _build_notification_sla_summary(
    notification_events: list[dict[str, object]],
    assignment_sla_seconds: int,
    severity_sla_overrides: dict[str, int] | None = None,
) -> list[dict[str, object]]:
    """计算已分派但仍未确认的 SLA 超时告警。"""
    severity_sla_overrides = severity_sla_overrides or {}
    if assignment_sla_seconds <= 0 and not any(value > 0 for value in severity_sla_overrides.values()):
        return []

    now = datetime.now(UTC)
    rows: list[dict[str, object]] = []
    for event in notification_events:
        if not str(event.get("assigned_to", "")).strip():
            continue
        if str(event.get("resolved_at", "")).strip():
            continue
        if str(event.get("acknowledged_at", "")).strip():
            continue
        anchor_text = str(event.get("assigned_at", "")).strip() or str(event.get("timestamp", "")).strip()
        if not anchor_text:
            continue
        try:
            anchor_at = datetime.fromisoformat(anchor_text)
        except ValueError:
            continue
        severity = str(event.get("severity", "")).strip().lower()
        effective_sla_seconds = max(int(severity_sla_overrides.get(severity, 0)), 0) or max(int(assignment_sla_seconds), 0)
        if effective_sla_seconds <= 0:
            continue
        age_seconds = int((now - anchor_at).total_seconds())
        if age_seconds < effective_sla_seconds:
            continue
        rows.append(
            {
                "event_id": str(event.get("event_id", "")),
                "owner": str(event.get("assigned_to", "")).strip(),
                "severity": str(event.get("severity", "")),
                "category": str(event.get("category", "")),
                "title": str(event.get("title", "")),
                "assigned_at": anchor_text,
                "age_seconds": age_seconds,
                "sla_seconds": effective_sla_seconds,
                "sla_source": severity if severity_sla_overrides.get(severity, 0) else "default",
                "breach_seconds": age_seconds - effective_sla_seconds,
            }
        )
    rows.sort(
        key=lambda item: (-int(item.get("breach_seconds", 0)), -int(item.get("age_seconds", 0)), str(item.get("owner", "")))
    )
    return rows


def _build_execution_requests(executions: list[dict[str, object]]) -> list[dict[str, object]]:
    """把多次 execution attempt 按 `request_id` 归并成请求级摘要。"""
    grouped: dict[str, list[dict[str, object]]] = {}
    for execution in executions:
        request_id = str(execution.get("request_id", ""))
        if not request_id:
            continue
        grouped.setdefault(request_id, []).append(execution)

    requests: list[dict[str, object]] = []
    for request_id, attempts in grouped.items():
        ordered = sorted(attempts, key=lambda item: str(item.get("started_at", "")))
        first = ordered[0]
        last = ordered[-1]
        failure_counter = Counter(
            str(item.get("failure_class", "")).strip()
            for item in ordered
            if str(item.get("failure_class", "")).strip()
        )
        failure_classes = [
            {"failure_class": failure_class, "count": count}
            for failure_class, count in sorted(failure_counter.items(), key=lambda item: (-item[1], item[0]))
        ]
        retry_scheduled_count = len([item for item in ordered if item.get("retry_decision") == "retry_scheduled"])
        final_failure_count = len([item for item in ordered if item.get("retry_decision") == "final_failure"])
        non_retryable_failure_count = len(
            [
                item
                for item in ordered
                if item.get("status") == "failed" and not bool(item.get("retryable"))
            ]
        )
        anomaly_score = retry_scheduled_count
        anomaly_score += final_failure_count * 3
        anomaly_score += non_retryable_failure_count * 2
        anomaly_score += sum(int(item.get("recovered_execution_count", 0)) for item in ordered)
        if last.get("status") == "blocked":
            anomaly_score += 4
        elif last.get("status") in {"failed", "abandoned"}:
            anomaly_score += 2
        if any(bool(item.get("protection_mode")) for item in ordered):
            anomaly_score += 2
        if len(ordered) > 1:
            anomaly_score += 1
        health_label = "healthy"
        if last.get("status") in {"failed", "blocked"} or final_failure_count or non_retryable_failure_count:
            health_label = "critical"
        elif last.get("status") == "abandoned" or retry_scheduled_count or any(
            bool(item.get("protection_mode")) for item in ordered
        ):
            health_label = "watch"
        requests.append(
            {
                "request_id": request_id,
                "symbol": last.get("symbol", ""),
                "timeframe": last.get("timeframe", ""),
                "attempt_count": len(ordered),
                "attempt_path": " -> ".join(str(item.get("status", "")) for item in ordered),
                "decision_path": " -> ".join(str(item.get("retry_decision", "")) for item in ordered if item.get("retry_decision")),
                "final_status": last.get("status", ""),
                "latest_execution_id": last.get("execution_id", ""),
                "run_id": last.get("run_id", ""),
                "retried": len(ordered) > 1,
                "blocked": last.get("status") == "blocked",
                "protection_mode_seen": any(bool(item.get("protection_mode")) for item in ordered),
                "cooldown_active": bool(last.get("protection_mode") and str(last.get("protection_cooldown_until", "")).strip()),
                "protection_cooldown_until": str(last.get("protection_cooldown_until", "") or ""),
                "requested_at": first.get("requested_at", ""),
                "last_updated_at": last.get("finished_at") or last.get("started_at", ""),
                "retry_scheduled_count": retry_scheduled_count,
                "final_failure_count": final_failure_count,
                "non_retryable_failure_count": non_retryable_failure_count,
                "failure_classes": failure_classes,
                "dominant_failure_class": failure_classes[0]["failure_class"] if failure_classes else "",
                "anomaly_score": anomaly_score,
                "health_label": health_label,
            }
        )
    requests.sort(key=lambda item: str(item.get("last_updated_at", "")), reverse=True)
    return requests


def _build_execution_request_details(executions: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    """把 execution attempt 按 `request_id` 聚合成明细，供历史页联动展示。"""
    grouped: dict[str, list[dict[str, object]]] = {}
    for execution in executions:
        request_id = str(execution.get("request_id", ""))
        if not request_id:
            continue
        grouped.setdefault(request_id, []).append(execution)
    for attempts in grouped.values():
        attempts.sort(key=lambda item: str(item.get("started_at", "")))
    return grouped


def build_dashboard_payload(
    backtest_result: dict[str, object],
    *,
    symbol: str,
    timeframe: str,
    initial_equity: float,
    settings: dict[str, dict[str, object]],
) -> dict[str, object]:
    """把单次回测结果整理成 dashboard 页面使用的数据格式。"""
    metrics = backtest_result["metrics"]
    trades = backtest_result["trades"]
    orders = backtest_result["orders"]
    audit_log = backtest_result["audit_log"]
    account = backtest_result["account"]
    equity_curve = backtest_result["equity_curve"]
    drawdown_curve = backtest_result["drawdown_curve"]

    latest_equity = equity_curve[-1]["equity"] if equity_curve else account["equity"]
    latest_drawdown = drawdown_curve[-1]["drawdown_pct"] if drawdown_curve else 0.0
    first_bar_at = equity_curve[0]["timestamp"] if equity_curve else ""
    last_bar_at = equity_curve[-1]["timestamp"] if equity_curve else ""
    drawdown_values = [float(item.get("drawdown_pct", 0.0)) for item in drawdown_curve]
    equity_values = [float(item.get("equity", 0.0)) for item in equity_curve]
    audit_blocked = len([event for event in audit_log if not bool(event.get("risk_allowed"))])
    audit_order_events = len([event for event in audit_log if str(event.get("event", "")).startswith("order_")])

    return {
        "run_context": {
            "symbol": symbol,
            "timeframe": timeframe,
            "strategy_name": settings.get("strategy", {}).get("name", ""),
            "bars_processed": backtest_result["bars_processed"],
            "initial_equity": initial_equity,
            "ending_equity": latest_equity,
            "first_bar_at": first_bar_at,
            "last_bar_at": last_bar_at,
        },
        # summary_cards 是顶部卡片的直接输入，前端不需要再额外拼装。
        "summary_cards": [
            {"id": "ending_equity", "label": "Ending Equity", "value": latest_equity},
            {"id": "total_return_pct", "label": "Total Return %", "value": metrics["total_return_pct"]},
            {"id": "max_drawdown_pct", "label": "Max Drawdown %", "value": metrics["max_drawdown_pct"]},
            {"id": "sharpe_ratio", "label": "Sharpe Ratio", "value": metrics["sharpe_ratio"]},
            {"id": "sortino_ratio", "label": "Sortino Ratio", "value": metrics["sortino_ratio"]},
            {"id": "profit_factor", "label": "Profit Factor", "value": metrics["profit_factor"]},
        ],
        "account_summary": account,
        "performance_summary": {
            "total_trades": metrics["total_trades"],
            "winning_trades": metrics["winning_trades"],
            "losing_trades": metrics["losing_trades"],
            "win_rate_pct": metrics["win_rate_pct"],
            "avg_trade_pnl": metrics["avg_trade_pnl"],
            "latest_drawdown_pct": latest_drawdown,
            "longest_underwater_bars": metrics["longest_underwater_bars"],
        },
        "charts": {
            "equity_curve": equity_curve,
            "drawdown_curve": drawdown_curve,
        },
        "chart_summary": {
            "bars_processed": backtest_result["bars_processed"],
            "first_bar_at": first_bar_at,
            "last_bar_at": last_bar_at,
            "equity_peak": max(equity_values) if equity_values else latest_equity,
            "equity_floor": min(equity_values) if equity_values else latest_equity,
            "deepest_drawdown_pct": max(drawdown_values) if drawdown_values else 0.0,
            "ending_drawdown_pct": latest_drawdown,
        },
        "order_summary": {
            "total_orders": len(orders),
            "open_orders": len([item for item in orders if item["status"] == "open"]),
            "replaced_orders": len([item for item in orders if item["status"] == "replaced"]),
            "filled_orders": len([item for item in orders if item["status"] == "filled"]),
            "partial_orders": len([item for item in orders if item["status"] == "partially_filled"]),
            "cancelled_orders": len([item for item in orders if item["status"] == "cancelled"]),
            "rejected_orders": len([item for item in orders if item["status"] == "rejected"]),
            "skipped_orders": len([item for item in orders if item["status"] == "skipped"]),
        },
        "audit_summary": {
            "total_events": len(audit_log),
            "risk_blocked_events": audit_blocked,
            "order_events": audit_order_events,
            "signals_evaluated": len([item for item in audit_log if item.get("event") == "signal_evaluated"]),
            "order_created_events": len([item for item in audit_log if item.get("event") == "order_created"]),
            "replaced_events": len([item for item in audit_log if item.get("event") == "order_replaced"]),
            "cancelled_events": len([item for item in audit_log if item.get("event") == "order_cancelled"]),
        },
        "config_sections": _format_config_sections(settings, symbol=symbol, timeframe=timeframe, initial_equity=initial_equity),
        "recent_trades": trades[-10:],
        "recent_orders": orders[-10:],
        "audit_timeline": audit_log[-20:],
    }


def build_history_payload(
    runs: list[dict[str, object]],
    executions: list[dict[str, object]],
    live_cycles: list[dict[str, object]],
    maintenance_cycles: list[dict[str, object]],
    broker_syncs: list[dict[str, object]],
    orders: list[dict[str, object]],
    audit_events: list[dict[str, object]],
    notification_events: list[dict[str, object]],
    notification_assignment_sla_seconds: int = 0,
    notification_assignment_sla_overrides: dict[str, int] | None = None,
    live_runner_stall_threshold_seconds: float = 0.0,
    maintenance_runner_stall_threshold_seconds: float = 0.0,
    broker_max_snapshot_age_seconds: int = 0,
    broker_reconcile_thresholds: dict[str, float] | None = None,
    latest_run_detail: dict[str, object] | None = None,
    latest_broker_sync_detail: dict[str, object] | None = None,
    runtime_reconcile_preview: dict[str, int] | None = None,
) -> dict[str, object]:
    """把历史运行结果整理成历史页所需的聚合结构。"""
    latest_run = runs[0] if runs else {}
    order_lifecycles = _build_order_lifecycles(orders)
    order_lifecycle_details = _build_order_lifecycle_details(orders)
    execution_requests = _build_execution_requests(executions)
    execution_request_details = _build_execution_request_details(executions)
    notification_summary = _build_notification_summary(notification_events)
    notification_owner_summary = _build_notification_owner_summary(notification_events)
    notification_inbox = _build_notification_inbox(notification_events)
    live_runner_summary = _build_live_runner_summary(
        live_cycles,
        stall_threshold_seconds=max(float(live_runner_stall_threshold_seconds), 0.0),
    )
    maintenance_summary = _build_maintenance_summary(maintenance_cycles)
    maintenance_runner_summary = _build_maintenance_runner_summary(
        maintenance_cycles,
        stall_threshold_seconds=max(float(maintenance_runner_stall_threshold_seconds), 0.0),
    )
    broker_sync_summary = _build_broker_sync_summary(broker_syncs)
    broker_health = _build_broker_health(
        broker_syncs,
        max_snapshot_age_seconds=max(int(broker_max_snapshot_age_seconds), 0),
    )
    broker_reconcile = _build_broker_reconcile(
        latest_run_detail,
        latest_broker_sync_detail,
        drift_thresholds=broker_reconcile_thresholds or {},
    )
    notification_sla_summary = _build_notification_sla_summary(
        notification_events,
        assignment_sla_seconds=max(int(notification_assignment_sla_seconds), 0),
        severity_sla_overrides=notification_assignment_sla_overrides or {},
    )
    controller_health = _build_controller_health(
        execution_requests=execution_requests,
        live_runner_summary=live_runner_summary,
        maintenance_runner_summary=maintenance_runner_summary,
        broker_health=broker_health,
        broker_reconcile=broker_reconcile,
        notification_events=notification_events,
        notification_sla_summary=notification_sla_summary,
        runtime_reconcile_preview=runtime_reconcile_preview or {},
    )
    request_anomalies = sorted(
        [item for item in execution_requests if item.get("anomaly_score", 0) > 0],
        key=lambda item: (-int(item.get("anomaly_score", 0)), str(item.get("last_updated_at", ""))),
    )
    failure_class_counter: Counter[str] = Counter()
    for request in execution_requests:
        for failure in request.get("failure_classes", []):
            failure_class = str(failure.get("failure_class", "")).strip()
            if failure_class:
                failure_class_counter[failure_class] += int(failure.get("count", 0))
    return {
        "history_summary": {
            "total_runs": len(runs),
            "total_executions": len(executions),
            "total_execution_requests": len(execution_requests),
            "retried_execution_requests": len([item for item in execution_requests if item.get("retried")]),
            "anomalous_execution_requests": len(request_anomalies),
            "critical_execution_requests": len(
                [item for item in execution_requests if item.get("health_label") == "critical"]
            ),
            "cooldown_protected_requests": len([item for item in execution_requests if item.get("cooldown_active")]),
            "total_live_cycles": len(live_cycles),
            "completed_live_cycles": len([item for item in live_cycles if item.get("status") == "completed"]),
            "skipped_live_cycles": len([item for item in live_cycles if item.get("status") == "skipped"]),
            "blocked_live_cycles": len([item for item in live_cycles if item.get("status") == "blocked"]),
            "failed_live_cycles": len([item for item in live_cycles if item.get("status") == "failed"]),
            "running_live_cycles": len([item for item in live_cycles if item.get("status") == "running"]),
            "live_runners": len(live_runner_summary),
            "idle_live_runners": len([item for item in live_runner_summary if int(item.get("idle_streak", 0)) > 0]),
            "stalled_live_runners": len([item for item in live_runner_summary if item.get("stalled")]),
            "total_maintenance_cycles": maintenance_summary["total_maintenance_cycles"],
            "failed_maintenance_cycles": maintenance_summary["failed_maintenance_cycles"],
            "latest_maintenance_status": maintenance_summary["latest_maintenance_status"],
            "latest_maintenance_at": maintenance_summary["latest_maintenance_at"],
            "maintenance_runners": len(maintenance_runner_summary),
            "stalled_maintenance_runners": len([item for item in maintenance_runner_summary if item.get("stalled")]),
            "total_broker_syncs": broker_sync_summary["total_broker_syncs"],
            "failed_broker_syncs": broker_sync_summary["failed_broker_syncs"],
            "stale_broker_syncs": int(bool(broker_health["stale"])),
            "broker_reconcile_mismatches": int(broker_reconcile["mismatch_count"]),
            "broker_reconcile_status": str(broker_reconcile["status"]),
            "latest_broker_sync_status": broker_sync_summary["latest_broker_sync_status"],
            "latest_broker_provider": broker_sync_summary["latest_broker_provider"],
            "latest_broker_equity": broker_sync_summary["latest_broker_equity"],
            "latest_broker_cash": broker_sync_summary["latest_broker_cash"],
            "latest_broker_positions": broker_sync_summary["latest_broker_positions"],
            "latest_broker_orders": broker_sync_summary["latest_broker_orders"],
            "latest_broker_synced_at": broker_sync_summary["latest_broker_synced_at"],
            "total_notifications": len(notification_events),
            "critical_notifications": len([item for item in notification_events if item.get("severity") == "critical"]),
            "queued_notifications": len([item for item in notification_events if item.get("delivery_status") == "queued"]),
            "pending_notifications": len(
                [
                    item
                    for item in notification_events
                    if item.get("delivery_status") in {"queued", "delivery_failed_retryable"}
                ]
            ),
            "dispatched_notifications": len(
                [item for item in notification_events if item.get("delivery_status") == "dispatched"]
            ),
            "failed_notifications": len(
                [
                    item
                    for item in notification_events
                    if item.get("delivery_status") in {"delivery_failed_retryable", "delivery_failed_final"}
                ]
            ),
            "scheduled_retry_notifications": len(
                [
                    item
                    for item in notification_events
                    if item.get("delivery_status") == "delivery_failed_retryable"
                    and str(item.get("next_delivery_attempt_at", "")).strip()
                ]
            ),
            "silenced_notification_groups": len(
                [item for item in notification_events if int(item.get("suppressed_duplicate_count", 0)) > 0]
            ),
            "suppressed_duplicates": sum(int(item.get("suppressed_duplicate_count", 0)) for item in notification_events),
            "acknowledged_notifications": len(
                [item for item in notification_events if str(item.get("acknowledged_at", "")).strip()]
            ),
            "unacknowledged_notifications": len(
                [item for item in notification_events if not str(item.get("acknowledged_at", "")).strip()]
            ),
            "resolved_notifications": len(
                [item for item in notification_events if str(item.get("resolved_at", "")).strip()]
            ),
            "reopened_notifications": len(
                [item for item in notification_events if int(item.get("reopen_count", 0)) > 0]
            ),
            "active_notifications": len(
                [item for item in notification_events if not str(item.get("resolved_at", "")).strip()]
            ),
            "assigned_notifications": len(
                [item for item in notification_events if str(item.get("assigned_to", "")).strip()]
            ),
            "unassigned_notifications": len(
                [item for item in notification_events if not str(item.get("assigned_to", "")).strip()]
            ),
            "escalated_notifications": len(
                [item for item in notification_events if str(item.get("escalated_at", "")).strip()]
            ),
            "escalated_unassigned_notifications": len(
                [
                    item
                    for item in notification_events
                    if str(item.get("escalated_at", "")).strip() and not str(item.get("assigned_to", "")).strip()
                ]
            ),
            "sla_breached_notifications": len(notification_sla_summary),
            "controller_health_issues": len(controller_health["issues"]),
            "stale_execution_candidates": int((runtime_reconcile_preview or {}).get("recovered_stale_executions", 0)),
            "runtime_reconcile_candidates": (
                int((runtime_reconcile_preview or {}).get("recovered_stale_executions", 0))
                + int((runtime_reconcile_preview or {}).get("repaired_assignment_timestamps", 0))
                + int((runtime_reconcile_preview or {}).get("repaired_resolution_acknowledgements", 0))
            ),
            "retry_scheduled_executions": len([item for item in executions if item.get("retry_decision") == "retry_scheduled"]),
            "failed_executions": len([item for item in executions if item.get("status") == "failed"]),
            "blocked_executions": len([item for item in executions if item.get("status") == "blocked"]),
            "running_executions": len([item for item in executions if item.get("status") == "running"]),
            "protection_mode_executions": len([item for item in executions if item.get("protection_mode")]),
            "recovered_execution_starts": sum(int(item.get("recovered_execution_count", 0)) for item in executions),
            "top_request_failure_class": (
                max(failure_class_counter.items(), key=lambda item: (item[1], item[0]))[0]
                if failure_class_counter
                else ""
            ),
            "latest_symbol": latest_run.get("symbol", ""),
            "latest_return_pct": latest_run.get("total_return_pct", 0.0),
            "latest_sharpe_ratio": latest_run.get("sharpe_ratio", 0.0),
            "total_lifecycles": len(order_lifecycles),
            "filled_lifecycles": len([item for item in order_lifecycles if item.get("final_status") == "filled"]),
            "cancelled_lifecycles": len([item for item in order_lifecycles if item.get("final_status") == "cancelled"]),
            "open_lifecycles": len([item for item in order_lifecycles if item.get("final_status") == "open"]),
            "repriced_lifecycles": len([item for item in order_lifecycles if "replaced" in str(item.get("status_path", ""))]),
        },
        "runs_table": runs,
        "execution_requests": execution_requests,
        "execution_request_details": execution_request_details,
        "request_anomalies": request_anomalies[:8],
        "recent_executions": executions,
        "recent_live_cycles": live_cycles,
        "live_runner_summary": live_runner_summary[:8],
        "recent_maintenance_cycles": maintenance_cycles,
        "maintenance_runner_summary": maintenance_runner_summary[:8],
        "recent_broker_syncs": broker_syncs,
        "broker_health": broker_health,
        "broker_reconcile": broker_reconcile,
        "notification_summary": notification_summary[:8],
        "notification_owner_summary": notification_owner_summary[:8],
        "notification_inbox": notification_inbox[:12],
        "notification_sla_summary": notification_sla_summary[:8],
        "controller_health": controller_health,
        "order_lifecycles": order_lifecycles,
        "order_lifecycle_details": order_lifecycle_details,
        "recent_orders": orders,
        "recent_audit_events": audit_events,
        "recent_notifications": notification_events,
    }
