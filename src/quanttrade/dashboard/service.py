from __future__ import annotations


def build_dashboard_payload(backtest_result: dict[str, object]) -> dict[str, object]:
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
    orders: list[dict[str, object]],
    audit_events: list[dict[str, object]],
) -> dict[str, object]:
    latest_run = runs[0] if runs else {}
    return {
        "history_summary": {
            "total_runs": len(runs),
            "latest_symbol": latest_run.get("symbol", ""),
            "latest_return_pct": latest_run.get("total_return_pct", 0.0),
            "latest_sharpe_ratio": latest_run.get("sharpe_ratio", 0.0),
        },
        "runs_table": runs,
        "recent_orders": orders,
        "recent_audit_events": audit_events,
    }
