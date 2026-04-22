import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoints (
    run_id TEXT NOT NULL,
    step_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (run_id, step_id)
);
CREATE INDEX IF NOT EXISTS idx_checkpoints_run_id ON checkpoints(run_id);
"""


class CheckpointStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @property
    def db_path(self) -> Path:
        return self._db_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save(self, run_id: str, step_id: int, label: str, data: dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
        timestamp = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints(run_id, step_id, label, data_json, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (run_id, step_id, label, payload, timestamp),
            )

    def latest(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT run_id, step_id, label, data_json, created_at FROM checkpoints "
                "WHERE run_id = ? ORDER BY step_id DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def all(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT run_id, step_id, label, data_json, created_at FROM checkpoints "
                "WHERE run_id = ? ORDER BY step_id ASC",
                (run_id,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def clear(self, run_id: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM checkpoints WHERE run_id = ?", (run_id,))
            return cursor.rowcount

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "run_id": row["run_id"],
            "step_id": row["step_id"],
            "label": row["label"],
            "data": json.loads(row["data_json"]),
            "created_at": row["created_at"],
        }
