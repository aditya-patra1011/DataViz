"""Keep named datasets in a SQLite file."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    name TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    date_columns TEXT NOT NULL,
    content TEXT NOT NULL
)
"""


class StorageError(ValueError):
    """Raised when a dataset cannot be saved or found."""


def _connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.execute(SCHEMA)
    return connection


def save(db_path: str | Path, name: str, df: pd.DataFrame, source: str) -> bool:
    """Save a dataset under a name. Returns True when it replaced an existing one."""
    name = name.strip()
    if not name:
        raise StorageError("Enter a name for this dataset.")
    dates = list(df.select_dtypes("datetime").columns)
    with closing(_connect(db_path)) as connection, connection:
        existed = (
            connection.execute("SELECT 1 FROM datasets WHERE name = ?", (name,)).fetchone()
            is not None
        )
        connection.execute(
            "INSERT OR REPLACE INTO datasets VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                source,
                datetime.now().strftime("%d %b %Y, %H:%M"),
                len(df),
                df.shape[1],
                json.dumps(dates),
                df.to_csv(index=False),
            ),
        )
    return existed


def list_saved(db_path: str | Path) -> list[dict]:
    """Every saved dataset, without its contents, sorted by name."""
    query = "SELECT name, source, saved_at, row_count, column_count FROM datasets ORDER BY name"
    with closing(_connect(db_path)) as connection:
        rows = connection.execute(query).fetchall()
    keys = ["name", "source", "saved_at", "rows", "columns"]
    return [dict(zip(keys, row, strict=True)) for row in rows]


def load(db_path: str | Path, name: str) -> tuple[pd.DataFrame, str]:
    """Return a saved dataset and where it originally came from."""
    query = "SELECT content, date_columns, source FROM datasets WHERE name = ?"
    with closing(_connect(db_path)) as connection:
        row = connection.execute(query, (name,)).fetchone()
    if row is None:
        raise StorageError(f"There is no saved dataset called '{name}'.")
    content, dates, source = row
    return pd.read_csv(StringIO(content), parse_dates=json.loads(dates)), source


def delete(db_path: str | Path, name: str) -> None:
    with closing(_connect(db_path)) as connection, connection:
        cursor = connection.execute("DELETE FROM datasets WHERE name = ?", (name,))
    if cursor.rowcount == 0:
        raise StorageError(f"There is no saved dataset called '{name}'.")
