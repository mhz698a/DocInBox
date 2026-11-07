from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.document_store import DocumentStore


class DocumentStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = DocumentStore(self.root / "inbox.sqlite3")
        self.document_path = self.root / "received.pdf"
        self.document_path.write_bytes(b"pdf data")
        self.store.add_document(
            document_id="doc-1",
            filename="received.pdf",
            stored_path=self.document_path,
            size=8,
            received_at="2026-11-06T12:00:00+00:00",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_document_is_persisted(self) -> None:
        documents = self.store.list_documents()
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["id"], "doc-1")
        self.assertEqual(documents[0]["status"], DocumentStore.PENDING)

    def test_status_can_be_changed_and_restored(self) -> None:
        self.assertTrue(self.store.set_status("doc-1", DocumentStore.HANDLED))
        self.assertEqual(self.store.get_document("doc-1")["status"], "handled")
        self.assertTrue(self.store.set_status("doc-1", DocumentStore.PENDING))
        self.assertEqual(self.store.get_document("doc-1")["status"], "pending")

    def test_delete_removes_file_and_database_record(self) -> None:
        self.assertTrue(self.store.delete_document("doc-1"))
        self.assertFalse(self.document_path.exists())
        self.assertIsNone(self.store.get_document("doc-1"))

    def test_clear_all_permanently_removes_files_and_records(self) -> None:
        second_path = self.root / "second.pdf"
        second_path.write_bytes(b"second")
        self.store.add_document(
            document_id="doc-2",
            filename="second.pdf",
            stored_path=second_path,
            size=6,
            received_at="2026-11-06T12:01:00+00:00",
        )

        deleted_count, failures = self.store.clear_all_documents()

        self.assertEqual(deleted_count, 2)
        self.assertEqual(failures, [])
        self.assertFalse(self.document_path.exists())
        self.assertFalse(second_path.exists())
        self.assertEqual(self.store.list_documents(), [])

    def test_clear_all_is_safe_when_files_are_already_missing(self) -> None:
        self.document_path.unlink()
        deleted_count, failures = self.store.clear_all_documents()
        self.assertEqual(deleted_count, 1)
        self.assertEqual(failures, [])
        self.assertEqual(self.store.list_documents(), [])

    def test_invalid_status_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.store.set_status("doc-1", "unknown")


if __name__ == "__main__":
    unittest.main()
