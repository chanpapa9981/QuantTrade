from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from quanttrade.core.types import MarketBar
from quanttrade.data.storage import connect_database


class BarRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def insert_bars(self, symbol: str, timeframe: str, bars: list[MarketBar]) -> int:
        connection = connect_database(self.db_path)
        try:
            payload = [
                (
                    symbol,
                    timeframe,
                    bar.timestamp.isoformat(),
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.volume,
                )
                for bar in bars
            ]
            connection.executemany(
                """
                INSERT OR REPLACE INTO bars(
                    symbol, timeframe, timestamp, open, high, low, close, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            return len(payload)
        finally:
            connection.close()

    def fetch_bars(self, symbol: str, timeframe: str = "1d") -> list[MarketBar]:
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "bars" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT timestamp, open, high, low, close, volume
                FROM bars
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp
                """,
                (symbol, timeframe),
            ).fetchall()
        finally:
            connection.close()

        return [
            MarketBar(
                timestamp=datetime.fromisoformat(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
            for row in rows
        ]


class BacktestRunRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def create_execution(self, symbol: str, timeframe: str, initial_equity: float) -> str:
        connection = connect_database(self.db_path)
        execution_id = str(uuid4())
        started_at = datetime.now(UTC).isoformat()
        try:
            connection.execute(
                """
                INSERT INTO backtest_executions (
                    execution_id, symbol, timeframe, initial_equity, status,
                    requested_at, started_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    symbol,
                    timeframe,
                    initial_equity,
                    "running",
                    started_at,
                    started_at,
                    "",
                ),
            )
            return execution_id
        finally:
            connection.close()

    def mark_execution_completed(self, execution_id: str, run_id: str) -> None:
        connection = connect_database(self.db_path)
        finished_at = datetime.now(UTC).isoformat()
        try:
            connection.execute(
                """
                UPDATE backtest_executions
                SET status = ?, finished_at = ?, run_id = ?, error_message = ''
                WHERE execution_id = ?
                """,
                ("completed", finished_at, run_id, execution_id),
            )
        finally:
            connection.close()

    def mark_execution_failed(self, execution_id: str, error_message: str, status: str = "failed") -> None:
        connection = connect_database(self.db_path)
        finished_at = datetime.now(UTC).isoformat()
        try:
            connection.execute(
                """
                UPDATE backtest_executions
                SET status = ?, finished_at = ?, error_message = ?
                WHERE execution_id = ?
                """,
                (status, finished_at, error_message[:500], execution_id),
            )
        finally:
            connection.close()

    def recover_stale_executions(self, symbol: str, timeframe: str) -> int:
        connection = connect_database(self.db_path)
        finished_at = datetime.now(UTC).isoformat()
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "backtest_executions" for table in tables):
                return 0
            rows = connection.execute(
                """
                SELECT execution_id
                FROM backtest_executions
                WHERE symbol = ? AND timeframe = ? AND status = ?
                """,
                (symbol, timeframe, "running"),
            ).fetchall()
            if not rows:
                return 0
            connection.execute(
                """
                UPDATE backtest_executions
                SET status = ?, finished_at = ?, error_message = ?
                WHERE symbol = ? AND timeframe = ? AND status = ?
                """,
                (
                    "abandoned",
                    finished_at,
                    "recovered after interrupted run",
                    symbol,
                    timeframe,
                    "running",
                ),
            )
            return len(rows)
        finally:
            connection.close()

    def save_run(self, symbol: str, timeframe: str, payload: dict[str, object]) -> str:
        connection = connect_database(self.db_path)
        run_id = str(uuid4())
        metrics = payload["metrics"]
        orders = payload["orders"]
        audit_log = payload["audit_log"]
        started_at = datetime.now(UTC).isoformat()
        try:
            connection.execute(
                """
                INSERT INTO backtest_runs (
                    run_id, symbol, timeframe, started_at, bars_processed, ending_equity,
                    total_return_pct, max_drawdown_pct, sharpe_ratio, sortino_ratio,
                    total_trades, winning_trades, losing_trades, avg_trade_pnl, profit_factor
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    symbol,
                    timeframe,
                    started_at,
                    payload["bars_processed"],
                    metrics["ending_equity"],
                    metrics["total_return_pct"],
                    metrics["max_drawdown_pct"],
                    metrics["sharpe_ratio"],
                    metrics["sortino_ratio"],
                    metrics["total_trades"],
                    metrics["winning_trades"],
                    metrics["losing_trades"],
                    metrics["avg_trade_pnl"],
                    metrics["profit_factor"],
                ),
            )
            if orders:
                connection.executemany(
                    """
                    INSERT INTO order_events (
                        run_id, timestamp, side, status, quantity, filled_quantity, remaining_quantity,
                        requested_price, fill_price, commission, gross_value, net_value, reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            order["timestamp"],
                            order["side"],
                            order["status"],
                            order["quantity"],
                            order.get("filled_quantity", 0),
                            order.get("remaining_quantity", 0),
                            order["requested_price"],
                            order["fill_price"],
                            order["commission"],
                            order.get("gross_value", 0.0),
                            order["net_value"],
                            order["reason"],
                        )
                        for order in orders
                    ],
                )
            if audit_log:
                connection.executemany(
                    """
                    INSERT INTO audit_events (
                        run_id, timestamp, event, signal, reason, risk_allowed
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            event["timestamp"],
                            event["event"],
                            event["signal"],
                            event["reason"],
                            event["risk_allowed"],
                        )
                        for event in audit_log
                    ],
                )
            account = payload["account"]
            connection.execute(
                """
                INSERT INTO account_snapshots (
                    run_id, recorded_at, cash, equity, realized_pnl, unrealized_pnl, open_positions
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    started_at,
                    account["cash"],
                    account["equity"],
                    account["realized_pnl"],
                    account["unrealized_pnl"],
                    account["open_positions"],
                ),
            )
            return run_id
        finally:
            connection.close()

    def fetch_recent_runs(self, limit: int = 10) -> list[dict[str, object]]:
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "backtest_runs" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT run_id, symbol, timeframe, started_at, bars_processed, ending_equity,
                       total_return_pct, max_drawdown_pct, sharpe_ratio, sortino_ratio, total_trades
                FROM backtest_runs
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()

        return [
            {
                "run_id": row[0],
                "symbol": row[1],
                "timeframe": row[2],
                "started_at": row[3],
                "bars_processed": row[4],
                "ending_equity": row[5],
                "total_return_pct": row[6],
                "max_drawdown_pct": row[7],
                "sharpe_ratio": row[8],
                "sortino_ratio": row[9],
                "total_trades": row[10],
            }
            for row in rows
        ]

    def fetch_recent_executions(self, limit: int = 10) -> list[dict[str, object]]:
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "backtest_executions" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT execution_id, symbol, timeframe, initial_equity, status,
                       requested_at, started_at, finished_at, run_id, error_message
                FROM backtest_executions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "execution_id": row[0],
                "symbol": row[1],
                "timeframe": row[2],
                "initial_equity": row[3],
                "status": row[4],
                "requested_at": row[5],
                "started_at": row[6],
                "finished_at": row[7],
                "run_id": row[8],
                "error_message": row[9],
            }
            for row in rows
        ]

    def fetch_run_detail(self, run_id: str) -> dict[str, object] | None:
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "backtest_runs" for table in tables):
                return None
            run_row = connection.execute(
                """
                SELECT run_id, symbol, timeframe, started_at, bars_processed, ending_equity,
                       total_return_pct, max_drawdown_pct, sharpe_ratio, sortino_ratio,
                       total_trades, winning_trades, losing_trades, avg_trade_pnl, profit_factor
                FROM backtest_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if run_row is None:
                return None

            order_rows = connection.execute(
                """
                SELECT timestamp, side, status, quantity, filled_quantity, remaining_quantity,
                       requested_price, fill_price, commission, gross_value, net_value, reason
                FROM order_events
                WHERE run_id = ?
                ORDER BY timestamp
                """,
                (run_id,),
            ).fetchall()
            audit_rows = connection.execute(
                """
                SELECT timestamp, event, signal, reason, risk_allowed
                FROM audit_events
                WHERE run_id = ?
                ORDER BY timestamp
                """,
                (run_id,),
            ).fetchall()
            snapshot_row = connection.execute(
                """
                SELECT recorded_at, cash, equity, realized_pnl, unrealized_pnl, open_positions
                FROM account_snapshots
                WHERE run_id = ?
                ORDER BY recorded_at DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        finally:
            connection.close()

        return {
            "run": {
                "run_id": run_row[0],
                "symbol": run_row[1],
                "timeframe": run_row[2],
                "started_at": run_row[3],
                "bars_processed": run_row[4],
                "ending_equity": run_row[5],
                "total_return_pct": run_row[6],
                "max_drawdown_pct": run_row[7],
                "sharpe_ratio": run_row[8],
                "sortino_ratio": run_row[9],
                "total_trades": run_row[10],
                "winning_trades": run_row[11],
                "losing_trades": run_row[12],
                "avg_trade_pnl": run_row[13],
                "profit_factor": run_row[14],
            },
            "orders": [
                {
                    "timestamp": row[0],
                    "side": row[1],
                    "status": row[2],
                    "quantity": row[3],
                    "filled_quantity": row[4],
                    "remaining_quantity": row[5],
                    "requested_price": row[6],
                    "fill_price": row[7],
                    "commission": row[8],
                    "gross_value": row[9],
                    "net_value": row[10],
                    "reason": row[11],
                }
                for row in order_rows
            ],
            "audit_log": [
                {
                    "timestamp": row[0],
                    "event": row[1],
                    "signal": row[2],
                    "reason": row[3],
                    "risk_allowed": row[4],
                }
                for row in audit_rows
            ],
            "account_snapshot": {
                "recorded_at": snapshot_row[0],
                "cash": snapshot_row[1],
                "equity": snapshot_row[2],
                "realized_pnl": snapshot_row[3],
                "unrealized_pnl": snapshot_row[4],
                "open_positions": snapshot_row[5],
            }
            if snapshot_row
            else {
                "recorded_at": run_row[3],
                "cash": run_row[5],
                "equity": run_row[5],
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "open_positions": 0,
            },
        }

    def fetch_recent_order_events(self, limit: int = 20) -> list[dict[str, object]]:
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "order_events" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT run_id, timestamp, side, status, quantity, filled_quantity, remaining_quantity,
                       fill_price, commission, reason
                FROM order_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "run_id": row[0],
                "timestamp": row[1],
                "side": row[2],
                "status": row[3],
                "quantity": row[4],
                "filled_quantity": row[5],
                "remaining_quantity": row[6],
                "fill_price": row[7],
                "commission": row[8],
                "reason": row[9],
            }
            for row in rows
        ]

    def fetch_recent_audit_events(self, limit: int = 20) -> list[dict[str, object]]:
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            if not any(table[0] == "audit_events" for table in tables):
                return []
            rows = connection.execute(
                """
                SELECT run_id, timestamp, event, signal, reason, risk_allowed
                FROM audit_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "run_id": row[0],
                "timestamp": row[1],
                "event": row[2],
                "signal": row[3],
                "reason": row[4],
                "risk_allowed": row[5],
            }
            for row in rows
        ]

    def fetch_history_bundle(self, runs_limit: int = 20, events_limit: int = 20) -> dict[str, list[dict[str, object]]]:
        connection = connect_database(self.db_path)
        try:
            tables = connection.execute("SHOW TABLES").fetchall()
            table_names = {table[0] for table in tables}
            runs: list[dict[str, object]] = []
            orders: list[dict[str, object]] = []
            audit_events: list[dict[str, object]] = []

            if "backtest_runs" in table_names:
                run_rows = connection.execute(
                    """
                    SELECT run_id, symbol, timeframe, started_at, bars_processed, ending_equity,
                           total_return_pct, max_drawdown_pct, sharpe_ratio, sortino_ratio, total_trades
                    FROM backtest_runs
                    ORDER BY started_at DESC
                    LIMIT ?
                    """,
                    (runs_limit,),
                ).fetchall()
                runs = [
                    {
                        "run_id": row[0],
                        "symbol": row[1],
                        "timeframe": row[2],
                        "started_at": row[3],
                        "bars_processed": row[4],
                        "ending_equity": row[5],
                        "total_return_pct": row[6],
                        "max_drawdown_pct": row[7],
                        "sharpe_ratio": row[8],
                        "sortino_ratio": row[9],
                        "total_trades": row[10],
                    }
                    for row in run_rows
                ]

            if "order_events" in table_names:
                order_rows = connection.execute(
                    """
                    SELECT run_id, timestamp, side, status, quantity, filled_quantity, remaining_quantity,
                           fill_price, commission, reason
                    FROM order_events
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (events_limit,),
                ).fetchall()
                orders = [
                    {
                        "run_id": row[0],
                        "timestamp": row[1],
                        "side": row[2],
                        "status": row[3],
                        "quantity": row[4],
                        "filled_quantity": row[5],
                        "remaining_quantity": row[6],
                        "fill_price": row[7],
                        "commission": row[8],
                        "reason": row[9],
                    }
                    for row in order_rows
                ]

            if "audit_events" in table_names:
                audit_rows = connection.execute(
                    """
                    SELECT run_id, timestamp, event, signal, reason, risk_allowed
                    FROM audit_events
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (events_limit,),
                ).fetchall()
                audit_events = [
                    {
                        "run_id": row[0],
                        "timestamp": row[1],
                        "event": row[2],
                        "signal": row[3],
                        "reason": row[4],
                        "risk_allowed": row[5],
                    }
                    for row in audit_rows
                ]
        finally:
            connection.close()

        return {
            "runs": runs,
            "orders": orders,
            "audit_events": audit_events,
        }
