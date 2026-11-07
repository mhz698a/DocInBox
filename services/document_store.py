"""Persistent metadata and actions for received documents."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class DocumentStore:
    """SQLite-backed inbox repository shared by Flask and the desktop UI."""

    PENDING = "pending"
    HANDLED = "handled"
    VALID_STATUSES = (PENDING, HANDLED)

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    size INTEGER NOT NULL CHECK(size > 0),
                    received_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'handled'))
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_documents_received_at
                ON documents(received_at DESC)
                """
            )
            connection.commit()
        finally:
            connection.close()

    def add_document(
        self,
        *,
        document_id: str,
        filename: str,
        stored_path: str | Path,
        size: int,
        received_at: str,
    ) -> None:
        if size <= 0:
            raise ValueError("El tamaño del documento debe ser mayor que cero.")
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO documents
                    (id, filename, stored_path, size, received_at, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    filename,
                    str(Path(stored_path).resolve()),
                    int(size),
                    received_at,
                    self.PENDING,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def list_documents(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT id, filename, stored_path, size, received_at, status
                FROM documents
                ORDER BY received_at DESC, rowid DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT id, filename, stored_path, size, received_at, status
                FROM documents WHERE id = ?
                """,
                (document_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def set_status(self, document_id: str, status: str) -> bool:
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Estado no válido: {status}")
        connection = self._connect()
        try:
            cursor = connection.execute(
                "UPDATE documents SET status = ? WHERE id = ?",
                (status, document_id),
            )
            connection.commit()
            return cursor.rowcount > 0
        finally:
            connection.close()

    def delete_document(self, document_id: str) -> bool:
        """Delete the stored file and its inbox record."""
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT stored_path FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            if row is None:
                return False

            Path(row["stored_path"]).unlink(missing_ok=True)
            connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            connection.commit()
            return True
        except OSError:
            connection.rollback()
            raise
        finally:
            connection.close()

    def clear_all_documents(self) -> tuple[int, list[str]]:
        """Permanently remove all stored documents and their inbox records.

        Files that cannot be deleted remain registered in SQLite so that the
        operator can identify and retry them. Missing files count as cleaned.
        """
        connection = self._connect()
        deleted_ids: list[str] = []
        failed_files: list[str] = []
        try:
            rows = connection.execute(
                "SELECT id, filename, stored_path FROM documents"
            ).fetchall()

            for row in rows:
                try:
                    Path(row["stored_path"]).unlink(missing_ok=True)
                    deleted_ids.append(row["id"])
                except OSError as exc:
                    failed_files.append(f"{row['filename']}: {exc}")

            if deleted_ids:
                connection.executemany(
                    "DELETE FROM documents WHERE id = ?",
                    ((document_id,) for document_id in deleted_ids),
                )
                connection.commit()
            return len(deleted_ids), failed_files
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
