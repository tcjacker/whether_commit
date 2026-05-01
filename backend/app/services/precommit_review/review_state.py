from __future__ import annotations

import os
import sqlite3
from pathlib import Path


class ReviewStateStore:
    def __init__(self, workspace_path: str) -> None:
        self.workspace_path = workspace_path
        self.db_path = Path(workspace_path) / ".precommit-review" / "state.sqlite"
        os.makedirs(self.db_path.parent, exist_ok=True)
        self._ensure_schema()

    def get_signal_status(self, signal_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("select status from signal_reviews where signal_id = ?", (signal_id,)).fetchone()
            return row[0] if row else None

    def get_hunk_status(self, hunk_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("select status from hunk_reviews where hunk_id = ?", (hunk_id,)).fetchone()
            return row[0] if row else None

    def get_file_status(self, file_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("select status from file_reviews where file_id = ?", (file_id,)).fetchone()
            return row[0] if row else None

    def update_signal_state(self, signal_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into signal_reviews(signal_id, status)
                values(?, ?)
                on conflict(signal_id) do update set status = excluded.status
                """,
                (signal_id, status),
            )

    def update_hunk_state(self, hunk_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into hunk_reviews(hunk_id, status)
                values(?, ?)
                on conflict(hunk_id) do update set status = excluded.status
                """,
                (hunk_id, status),
            )

    def update_file_state(self, file_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into file_reviews(file_id, status)
                values(?, ?)
                on conflict(file_id) do update set status = excluded.status
                """,
                (file_id, status),
            )

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists signal_reviews (
                    signal_id text primary key,
                    status text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists hunk_reviews (
                    hunk_id text primary key,
                    status text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists file_reviews (
                    file_id text primary key,
                    status text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
