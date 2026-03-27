from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from quanttrade.core.types import MarketBar
from quanttrade.data.repository import BarRepository
from quanttrade.data.schema import create_schema


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported timestamp format: {value}") from exc
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp


def import_bars_from_csv(
    csv_path: str | Path,
    db_path: str,
    symbol: str,
    timeframe: str = "1d",
) -> int:
    create_schema(db_path)
    rows: list[MarketBar] = []
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("CSV must include timestamp, open, high, low, close, volume columns.")

        for row in reader:
            rows.append(
                MarketBar(
                    timestamp=_parse_timestamp(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )

    repository = BarRepository(db_path)
    return repository.insert_bars(symbol=symbol, timeframe=timeframe, bars=rows)
