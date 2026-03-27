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
        if args.output:
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

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
