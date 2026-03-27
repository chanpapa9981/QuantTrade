from __future__ import annotations

from quanttrade.data.storage import connect_database


def create_schema(db_path: str) -> None:
    connection = connect_database(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bars (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL DEFAULT '1d',
                timestamp TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                PRIMARY KEY (symbol, timeframe, timestamp)
            );

            CREATE INDEX IF NOT EXISTS idx_bars_symbol_timeframe_timestamp
            ON bars(symbol, timeframe, timestamp);

            CREATE TABLE IF NOT EXISTS backtest_runs (
                run_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                started_at TEXT NOT NULL,
                bars_processed INTEGER NOT NULL,
                ending_equity REAL NOT NULL,
                total_return_pct REAL NOT NULL,
                max_drawdown_pct REAL NOT NULL,
                sharpe_ratio REAL NOT NULL,
                sortino_ratio REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                winning_trades INTEGER NOT NULL,
                losing_trades INTEGER NOT NULL,
                avg_trade_pnl REAL NOT NULL,
                profit_factor REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_events (
                run_id TEXT NOT NULL,
                order_id TEXT NOT NULL DEFAULT '',
                timestamp TEXT NOT NULL,
                side TEXT NOT NULL,
                status TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                filled_quantity INTEGER NOT NULL DEFAULT 0,
                remaining_quantity INTEGER NOT NULL DEFAULT 0,
                requested_price REAL NOT NULL,
                fill_price REAL NOT NULL,
                commission REAL NOT NULL,
                gross_value REAL NOT NULL,
                net_value REAL NOT NULL,
                reason TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                run_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event TEXT NOT NULL,
                signal TEXT NOT NULL,
                reason TEXT NOT NULL,
                risk_allowed INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS account_snapshots (
                run_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                cash REAL NOT NULL,
                equity REAL NOT NULL,
                realized_pnl REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                open_positions INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS backtest_executions (
                execution_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                initial_equity REAL NOT NULL,
                status TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                run_id TEXT,
                error_message TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_backtest_executions_symbol_timeframe_status
            ON backtest_executions(symbol, timeframe, status, started_at);
            """
        )
        connection.execute("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS order_id TEXT DEFAULT '';")
        connection.execute("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS filled_quantity INTEGER DEFAULT 0;")
        connection.execute("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS remaining_quantity INTEGER DEFAULT 0;")
    finally:
        connection.close()
