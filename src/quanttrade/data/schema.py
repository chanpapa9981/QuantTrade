"""数据库表结构定义。"""

from __future__ import annotations

from quanttrade.data.storage import connect_database


def create_schema(db_path: str) -> None:
    """创建项目所需的数据表，并兼容旧库字段升级。"""
    connection = connect_database(db_path)
    try:
        # 这里集中创建项目当前阶段需要的所有核心表。
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
                broker_status TEXT NOT NULL DEFAULT '',
                status_detail TEXT NOT NULL DEFAULT '',
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

            CREATE TABLE IF NOT EXISTS notification_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                provider TEXT NOT NULL,
                delivery_status TEXT NOT NULL,
                delivery_target TEXT NOT NULL DEFAULT '',
                delivery_attempts INTEGER NOT NULL DEFAULT 0,
                delivered_at TEXT NOT NULL DEFAULT '',
                last_error TEXT NOT NULL DEFAULT '',
                next_delivery_attempt_at TEXT NOT NULL DEFAULT '',
                notification_key TEXT NOT NULL DEFAULT '',
                silenced_until TEXT NOT NULL DEFAULT '',
                suppressed_duplicate_count INTEGER NOT NULL DEFAULT 0,
                last_suppressed_at TEXT NOT NULL DEFAULT '',
                acknowledged_at TEXT NOT NULL DEFAULT '',
                acknowledged_note TEXT NOT NULL DEFAULT '',
                escalated_at TEXT NOT NULL DEFAULT '',
                escalation_level TEXT NOT NULL DEFAULT '',
                escalation_reason TEXT NOT NULL DEFAULT '',
                symbol TEXT NOT NULL DEFAULT '',
                timeframe TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                execution_id TEXT NOT NULL DEFAULT '',
                request_id TEXT NOT NULL DEFAULT ''
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
                request_id TEXT NOT NULL DEFAULT '',
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                initial_equity REAL NOT NULL,
                attempt_number INTEGER NOT NULL DEFAULT 1,
                recovered_execution_count INTEGER NOT NULL DEFAULT 0,
                consecutive_failures_before_start INTEGER NOT NULL DEFAULT 0,
                protection_mode INTEGER NOT NULL DEFAULT 0,
                protection_reason TEXT NOT NULL DEFAULT '',
                protection_cooldown_until TEXT NOT NULL DEFAULT '',
                retryable INTEGER NOT NULL DEFAULT 0,
                retry_decision TEXT NOT NULL DEFAULT '',
                failure_class TEXT NOT NULL DEFAULT '',
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
        # 历史版本数据库可能没有这些字段，所以这里用增量迁移方式自动补齐。
        connection.execute("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS order_id TEXT DEFAULT '';")
        connection.execute("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS filled_quantity INTEGER DEFAULT 0;")
        connection.execute("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS remaining_quantity INTEGER DEFAULT 0;")
        connection.execute("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS broker_status TEXT DEFAULT '';")
        connection.execute("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS status_detail TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS delivery_target TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS delivery_attempts INTEGER DEFAULT 0;")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS delivered_at TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS last_error TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS next_delivery_attempt_at TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS notification_key TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS silenced_until TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS suppressed_duplicate_count INTEGER DEFAULT 0;")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS last_suppressed_at TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS acknowledged_at TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS acknowledged_note TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS escalated_at TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS escalation_level TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS escalation_reason TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS symbol TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS timeframe TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS run_id TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS execution_id TEXT DEFAULT '';")
        connection.execute("ALTER TABLE notification_events ADD COLUMN IF NOT EXISTS request_id TEXT DEFAULT '';")
        connection.execute("ALTER TABLE backtest_executions ADD COLUMN IF NOT EXISTS request_id TEXT DEFAULT '';")
        connection.execute("ALTER TABLE backtest_executions ADD COLUMN IF NOT EXISTS attempt_number INTEGER DEFAULT 1;")
        connection.execute("ALTER TABLE backtest_executions ADD COLUMN IF NOT EXISTS recovered_execution_count INTEGER DEFAULT 0;")
        connection.execute("ALTER TABLE backtest_executions ADD COLUMN IF NOT EXISTS consecutive_failures_before_start INTEGER DEFAULT 0;")
        connection.execute("ALTER TABLE backtest_executions ADD COLUMN IF NOT EXISTS protection_mode INTEGER DEFAULT 0;")
        connection.execute("ALTER TABLE backtest_executions ADD COLUMN IF NOT EXISTS protection_reason TEXT DEFAULT '';")
        connection.execute("ALTER TABLE backtest_executions ADD COLUMN IF NOT EXISTS protection_cooldown_until TEXT DEFAULT '';")
        connection.execute("ALTER TABLE backtest_executions ADD COLUMN IF NOT EXISTS retryable INTEGER DEFAULT 0;")
        connection.execute("ALTER TABLE backtest_executions ADD COLUMN IF NOT EXISTS retry_decision TEXT DEFAULT '';")
        connection.execute("ALTER TABLE backtest_executions ADD COLUMN IF NOT EXISTS failure_class TEXT DEFAULT '';")
    finally:
        connection.close()
