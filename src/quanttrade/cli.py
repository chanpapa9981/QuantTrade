from __future__ import annotations

import argparse
import json

from quanttrade.app import QuantTradeApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QuantTrade command line interface")
    parser.add_argument(
        "--config",
        default="configs/settings.example.yaml",
        help="Path to YAML settings file",
    )

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
    run_detail_parser = subparsers.add_parser("run-detail", help="Show one persisted backtest run detail")
    run_detail_parser.add_argument("--run-id", required=True, help="Persisted run id")
    orders_parser = subparsers.add_parser("orders", help="List recent persisted order events")
    orders_parser.add_argument("--limit", type=int, default=20, help="Number of order events to list")
    audit_parser = subparsers.add_parser("audit-events", help="List recent persisted audit events")
    audit_parser.add_argument("--limit", type=int, default=20, help="Number of audit events to list")
    history_parser = subparsers.add_parser("history", help="Build dashboard-ready historical summary")
    history_parser.add_argument("--runs-limit", type=int, default=20, help="Number of runs to include")
    history_parser.add_argument("--events-limit", type=int, default=20, help="Number of order/audit events to include")
    history_html_parser = subparsers.add_parser("history-html", help="Build a static history HTML file")
    history_html_parser.add_argument("--runs-limit", type=int, default=20, help="Number of runs to include")
    history_html_parser.add_argument("--events-limit", type=int, default=20, help="Number of order/audit events to include")
    history_html_parser.add_argument("--output", default="var/reports/history.html", help="Output HTML path")
    return parser


def main() -> None:
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

    if args.command == "run-detail":
        print(json.dumps(app.backtest_run_detail(run_id=args.run_id), indent=2, ensure_ascii=False))
        return

    if args.command == "orders":
        print(json.dumps(app.recent_order_events(limit=args.limit), indent=2, ensure_ascii=False))
        return

    if args.command == "audit-events":
        print(json.dumps(app.recent_audit_events(limit=args.limit), indent=2, ensure_ascii=False))
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
