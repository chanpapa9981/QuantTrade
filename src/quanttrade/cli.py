"""命令行入口。

这个文件只做两件事：
1. 定义命令和参数长什么样；
2. 根据命令把请求转给 `QuantTradeApp`。

也就是说，CLI 只负责“接线”和“打印”，不应该直接塞复杂业务逻辑。
"""

from __future__ import annotations

import argparse
import json

from quanttrade.app import QuantTradeApp


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="QuantTrade command line interface")
    parser.add_argument(
        "--config",
        default="configs/settings.example.yaml",
        help="Path to YAML settings file",
    )

    # 每个子命令都对应 QuantTrade 的一个高层能力。
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="Validate config and print effective settings")
    subparsers.add_parser("run-sample", help="Run a single sample strategy step")
    import_parser = subparsers.add_parser("import-csv", help="Import OHLCV bars from CSV")
    import_parser.add_argument("--csv", required=True, help="CSV file with timestamp/open/high/low/close/volume")
    import_parser.add_argument("--symbol", required=True, help="Ticker symbol")
    import_parser.add_argument("--timeframe", default="1d", help="Bar timeframe")
    backtest_parser = subparsers.add_parser("backtest", help="Run historical backtest for a symbol")
    backtest_parser.add_argument("--symbol", required=True, help="Ticker symbol")
    backtest_parser.add_argument("--timeframe", default="1d", help="Bar timeframe")
    backtest_parser.add_argument("--initial-equity", type=float, default=100_000.0, help="Starting equity")
    backtest_parser.add_argument("--output", help="Optional path to write JSON backtest report")
    backtest_parser.add_argument("--persist", action="store_true", help="Persist the backtest run into the database")
    dashboard_parser = subparsers.add_parser("dashboard-data", help="Build dashboard-ready JSON payload")
    dashboard_parser.add_argument("--symbol", required=True, help="Ticker symbol")
    dashboard_parser.add_argument("--timeframe", default="1d", help="Bar timeframe")
    dashboard_parser.add_argument("--initial-equity", type=float, default=100_000.0, help="Starting equity")
    dashboard_parser.add_argument("--output", help="Optional path to write dashboard JSON")
    dashboard_html_parser = subparsers.add_parser("dashboard-html", help="Build a static dashboard HTML file")
    dashboard_html_parser.add_argument("--symbol", required=True, help="Ticker symbol")
    dashboard_html_parser.add_argument("--timeframe", default="1d", help="Bar timeframe")
    dashboard_html_parser.add_argument("--initial-equity", type=float, default=100_000.0, help="Starting equity")
    dashboard_html_parser.add_argument("--output", default="var/reports/dashboard.html", help="Output HTML path")
    runs_parser = subparsers.add_parser("runs", help="List recent persisted backtest runs")
    runs_parser.add_argument("--limit", type=int, default=10, help="Number of runs to list")
    execution_requests_parser = subparsers.add_parser("execution-requests", help="List recent request-level execution chains")
    execution_requests_parser.add_argument("--limit", type=int, default=10, help="Number of request chains to list")
    executions_parser = subparsers.add_parser("executions", help="List recent backtest execution attempts")
    executions_parser.add_argument("--limit", type=int, default=10, help="Number of executions to list")
    execution_detail_parser = subparsers.add_parser("execution-detail", help="Show one backtest execution detail")
    execution_detail_parser.add_argument("--execution-id", required=True, help="Execution attempt id")
    execution_request_detail_parser = subparsers.add_parser("execution-request-detail", help="Show one request-level execution chain detail")
    execution_request_detail_parser.add_argument("--request-id", required=True, help="Execution request id")
    protection_status_parser = subparsers.add_parser("protection-status", help="Show protection mode state for one symbol/timeframe")
    protection_status_parser.add_argument("--symbol", required=True, help="Ticker symbol")
    protection_status_parser.add_argument("--timeframe", default="1d", help="Bar timeframe")
    run_detail_parser = subparsers.add_parser("run-detail", help="Show one persisted backtest run detail")
    run_detail_parser.add_argument("--run-id", required=True, help="Persisted run id")
    orders_parser = subparsers.add_parser("orders", help="List recent persisted order events")
    orders_parser.add_argument("--limit", type=int, default=20, help="Number of order events to list")
    order_detail_parser = subparsers.add_parser("order-detail", help="Show one persisted order lifecycle detail")
    order_detail_parser.add_argument("--order-id", required=True, help="Persisted order id")
    audit_parser = subparsers.add_parser("audit-events", help="List recent persisted audit events")
    audit_parser.add_argument("--limit", type=int, default=20, help="Number of audit events to list")
    notifications_parser = subparsers.add_parser("notifications", help="List recent notification events")
    notifications_parser.add_argument("--limit", type=int, default=20, help="Number of notification events to list")
    notification_summary_parser = subparsers.add_parser("notification-summary", help="Show aggregated notification summary rows")
    notification_summary_parser.add_argument("--limit", type=int, default=50, help="Number of recent notification events to aggregate")
    notification_owner_summary_parser = subparsers.add_parser("notification-owner-summary", help="Show aggregated notification owner workload rows")
    notification_owner_summary_parser.add_argument("--limit", type=int, default=50, help="Number of recent notification events to aggregate")
    notification_ack_parser = subparsers.add_parser("notification-ack", help="Mark one notification event as acknowledged")
    notification_ack_parser.add_argument("--event-id", required=True, help="Notification event id")
    notification_ack_parser.add_argument("--note", default="", help="Optional acknowledgement note")
    notification_assign_parser = subparsers.add_parser("notification-assign", help="Assign one notification event to an owner")
    notification_assign_parser.add_argument("--event-id", required=True, help="Notification event id")
    notification_assign_parser.add_argument("--owner", required=True, help="Owner or operator name")
    notification_assign_parser.add_argument("--note", default="", help="Optional assignment note")
    notification_escalate_parser = subparsers.add_parser("notification-escalate", help="Escalate stale unacknowledged notification events")
    notification_escalate_parser.add_argument("--limit", type=int, default=50, help="Number of recent notification events to inspect")
    notifications_deliver_parser = subparsers.add_parser(
        "notifications-deliver",
        help="Process queued notification events through the local delivery worker",
    )
    notifications_deliver_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of queued notification events to process",
    )
    history_parser = subparsers.add_parser("history", help="Build dashboard-ready historical summary")
    history_parser.add_argument("--runs-limit", type=int, default=20, help="Number of runs to include")
    history_parser.add_argument("--events-limit", type=int, default=20, help="Number of order/audit events to include")
    history_html_parser = subparsers.add_parser("history-html", help="Build a static history HTML file")
    history_html_parser.add_argument("--runs-limit", type=int, default=20, help="Number of runs to include")
    history_html_parser.add_argument("--events-limit", type=int, default=20, help="Number of order/audit events to include")
    history_html_parser.add_argument("--output", default="var/reports/history.html", help="Output HTML path")
    return parser


def main() -> None:
    """CLI 主入口。

    解析参数后，把不同命令分发给 `QuantTradeApp`，最后统一用 JSON 打印结果。
    """
    parser = build_parser()
    args = parser.parse_args()
    app = QuantTradeApp(args.config)

    if args.command == "doctor":
        print(json.dumps(app.doctor(), indent=2, ensure_ascii=False))
        return

    if args.command == "run-sample":
        print(json.dumps(app.run_sample(), indent=2, ensure_ascii=False))
        return

    if args.command == "import-csv":
        print(
            json.dumps(
                app.import_csv(csv_path=args.csv, symbol=args.symbol, timeframe=args.timeframe),
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if args.command == "backtest":
        # `backtest` 有三种用法：
        # 1. 只运行并返回结果；
        # 2. 导出 JSON 报告；
        # 3. 直接落库，形成可追踪的历史记录。
        if args.persist:
            payload = app.persist_backtest_run(
                symbol=args.symbol,
                timeframe=args.timeframe,
                initial_equity=args.initial_equity,
            )
        elif args.output:
            payload = app.export_backtest(
                symbol=args.symbol,
                timeframe=args.timeframe,
                initial_equity=args.initial_equity,
                output_path=args.output,
            )
        else:
            payload = app.backtest_symbol(
                symbol=args.symbol,
                timeframe=args.timeframe,
                initial_equity=args.initial_equity,
            )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if args.command == "dashboard-data":
        if args.output:
            payload = app.export_dashboard_snapshot(
                symbol=args.symbol,
                timeframe=args.timeframe,
                initial_equity=args.initial_equity,
                output_path=args.output,
            )
        else:
            payload = app.dashboard_snapshot(
                symbol=args.symbol,
                timeframe=args.timeframe,
                initial_equity=args.initial_equity,
            )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if args.command == "dashboard-html":
        payload = app.export_dashboard_html(
            symbol=args.symbol,
            timeframe=args.timeframe,
            initial_equity=args.initial_equity,
            output_path=args.output,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if args.command == "runs":
        print(json.dumps(app.recent_backtest_runs(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "execution-requests":
        print(json.dumps(app.recent_execution_requests(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "executions":
        print(json.dumps(app.recent_backtest_executions(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "execution-detail":
        print(json.dumps(app.execution_detail(execution_id=args.execution_id), indent=2, ensure_ascii=False))
        return

    if args.command == "execution-request-detail":
        print(json.dumps(app.execution_request_detail(request_id=args.request_id), indent=2, ensure_ascii=False))
        return

    if args.command == "protection-status":
        print(json.dumps(app.protection_status(symbol=args.symbol, timeframe=args.timeframe), indent=2, ensure_ascii=False))
        return

    if args.command == "run-detail":
        print(json.dumps(app.backtest_run_detail(run_id=args.run_id), indent=2, ensure_ascii=False))
        return

    if args.command == "orders":
        print(json.dumps(app.recent_order_events(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "order-detail":
        print(json.dumps(app.order_detail(order_id=args.order_id), indent=2, ensure_ascii=False))
        return

    if args.command == "audit-events":
        print(json.dumps(app.recent_audit_events(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "notifications":
        print(json.dumps(app.recent_notification_events(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "notification-summary":
        print(json.dumps(app.notification_summary(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "notification-owner-summary":
        print(json.dumps(app.notification_owner_summary(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "notification-ack":
        print(json.dumps(app.acknowledge_notification(event_id=args.event_id, note=args.note), indent=2, ensure_ascii=False))
        return

    if args.command == "notification-assign":
        print(
            json.dumps(
                app.assign_notification(event_id=args.event_id, owner=args.owner, note=args.note),
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if args.command == "notification-escalate":
        print(json.dumps(app.escalate_notifications(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "notifications-deliver":
        print(json.dumps(app.deliver_notifications(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "history":
        print(
            json.dumps(
                app.dashboard_history(runs_limit=args.runs_limit, events_limit=args.events_limit),
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if args.command == "history-html":
        print(
            json.dumps(
                app.export_history_html(
                    runs_limit=args.runs_limit,
                    events_limit=args.events_limit,
                    output_path=args.output,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
