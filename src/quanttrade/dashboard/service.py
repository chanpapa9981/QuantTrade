"""Dashboard 数据整理层。

这个模块不负责画页面，而是负责把原始回测/历史数据重新整理成前端更容易消费的结构。
"""

from __future__ import annotations


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


def build_dashboard_payload(backtest_result: dict[str, object]) -> dict[str, object]:
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

    return {
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
        "recent_trades": trades[-10:],
        "recent_orders": orders[-10:],
        "audit_timeline": audit_log[-20:],
    }


def build_history_payload(
    runs: list[dict[str, object]],
    executions: list[dict[str, object]],
    orders: list[dict[str, object]],
    audit_events: list[dict[str, object]],
) -> dict[str, object]:
    """把历史运行结果整理成历史页所需的聚合结构。"""
    latest_run = runs[0] if runs else {}
    order_lifecycles = _build_order_lifecycles(orders)
    order_lifecycle_details = _build_order_lifecycle_details(orders)
    return {
        "history_summary": {
            "total_runs": len(runs),
            "total_executions": len(executions),
            "failed_executions": len([item for item in executions if item.get("status") == "failed"]),
            "running_executions": len([item for item in executions if item.get("status") == "running"]),
            "protection_mode_executions": len([item for item in executions if item.get("protection_mode")]),
            "recovered_execution_starts": sum(int(item.get("recovered_execution_count", 0)) for item in executions),
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
        "recent_executions": executions,
        "order_lifecycles": order_lifecycles,
        "order_lifecycle_details": order_lifecycle_details,
        "recent_orders": orders,
        "recent_audit_events": audit_events,
    }
