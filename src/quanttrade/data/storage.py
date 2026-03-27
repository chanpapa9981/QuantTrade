from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import duckdb


def ensure_data_dirs(duckdb_path: str) -> Path:
    path = Path(duckdb_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def lock_path_for(db_path: str) -> Path:
    db_file = ensure_data_dirs(db_path)
    lock_dir = db_file.parent / ".locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir / f"{db_file.name}.lock"


@contextmanager
def database_lock(db_path: str) -> Iterator[None]:
    path = lock_path_for(db_path)
    with path.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
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
