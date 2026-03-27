from __future__ import annotations

import os
from pathlib import Path

import duckdb


def ensure_data_dirs(duckdb_path: str) -> Path:
    path = Path(duckdb_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


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
