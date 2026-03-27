from __future__ import annotations

from datetime import datetime

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
