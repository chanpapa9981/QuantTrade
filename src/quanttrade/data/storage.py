from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import duckdb


class LockUnavailableError(RuntimeError):
    """Raised when a non-blocking execution lock cannot be acquired."""


def ensure_data_dirs(duckdb_path: str) -> Path:
    path = Path(duckdb_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def lock_path_for(db_path: str) -> Path:
    db_file = ensure_data_dirs(db_path)
    lock_dir = db_file.parent / ".locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir / f"{db_file.name}.lock"


def execution_lock_path_for(db_path: str, symbol: str, timeframe: str) -> Path:
    db_file = ensure_data_dirs(db_path)
    lock_dir = db_file.parent / ".locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_name = f"{db_file.name}.{symbol.lower()}.{timeframe.lower()}.run.lock"
    return lock_dir / lock_name


@contextmanager
def database_lock(db_path: str) -> Iterator[None]:
    path = lock_path_for(db_path)
    with path.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def execution_lock(db_path: str, symbol: str, timeframe: str, blocking: bool = False) -> Iterator[None]:
    path = execution_lock_path_for(db_path, symbol, timeframe)
    with path.open("w", encoding="utf-8") as handle:
        lock_mode = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
        try:
            fcntl.flock(handle.fileno(), lock_mode)
        except BlockingIOError as exc:
            raise LockUnavailableError(f"backtest already running for {symbol} {timeframe}") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def connect_database(db_path: str) -> duckdb.DuckDBPyConnection:
    path = ensure_data_dirs(db_path)
    duckdb_home = path.parent / ".duckdb_home"
    duckdb_home.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(duckdb_home)
    os.environ["DUCKDB_HOME"] = str(duckdb_home)
    return duckdb.connect(
        str(path),
        config={
            "home_directory": str(duckdb_home),
            "temp_directory": str(duckdb_home / "tmp"),
        },
    )
