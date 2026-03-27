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
            """
        )
    finally:
        connection.close()
