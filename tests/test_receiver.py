from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from app_flask import create_app
from services.file_policy import SUPPORTED_EXTENSIONS


class ReceiverApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.upload_dir = self.root / "received"
        self.app = create_app(
            {
                "TESTING": True,
                "UPLOAD_FOLDER": self.upload_dir,
                "DATABASE_PATH": self.root / "inbox.sqlite3",
                "MAX_CONTENT_LENGTH": 2 * 1024 * 1024,
                "MAX_UPLOAD_BYTES": 1024 * 1024,
                "MAX_UPLOAD_MB": 1,
                "ACCESS_TOKEN": "",
                "ALLOWED_EXTENSIONS": set(SUPPORTED_EXTENSIONS),
            }
        )
        self.client = self.app.test_client()
        self.store = self.app.extensions["document_store"]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_health_endpoint(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_upload_page_and_assets_are_available(self) -> None:
        page = self.client.get("/")
        script = self.client.get("/assets/app.js")
        stylesheet = self.client.get("/assets/s.css")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Envía tus documentos".encode("utf-8"), page.data)
        self.assertIn(b'accept=".doc,.docx', page.data)
        self.assertEqual(script.status_code, 200)
        self.assertEqual(stylesheet.status_code, 200)

    def test_upload_saves_file_and_registers_arrival(self) -> None:
        response = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b"document contents"), "invoice 2026.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        saved_files = list(self.upload_dir.iterdir())
        self.assertEqual(len(saved_files), 1)
        self.assertEqual(saved_files[0].read_bytes(), b"document contents")
        self.assertTrue(saved_files[0].name.endswith("_invoice_2026.pdf"))
        self.assertEqual(payload["filename"], "invoice_2026.pdf")
        self.assertEqual(payload["size"], len(b"document contents"))
        self.assertEqual(payload["status"], "pending")
        documents = self.store.list_documents()
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["id"], payload["id"])
        self.assertEqual(documents[0]["stored_path"], str(saved_files[0].resolve()))

    def test_extension_check_is_case_insensitive(self) -> None:
        response = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b"pdf"), "REPORT.PDF")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 201)

    def test_upload_rejects_disabled_extension(self) -> None:
        self.app.config["ALLOWED_EXTENSIONS"] = {"pdf"}
        response = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b"payload"), "program.exe")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 415)
        self.assertIn("no permitido", response.get_json()["error"])
        self.assertEqual(list(self.upload_dir.iterdir()), [])

    def test_same_filename_does_not_overwrite_previous_upload(self) -> None:
        for content in (b"first", b"second"):
            response = self.client.post(
                "/api/upload",
                data={"file": (io.BytesIO(content), "same.pdf")},
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 201)
        saved_files = list(self.upload_dir.iterdir())
        self.assertEqual(len(saved_files), 2)
        self.assertEqual({path.read_bytes() for path in saved_files}, {b"first", b"second"})
        self.assertEqual(len(self.store.list_documents()), 2)

    def test_upload_rejects_missing_file(self) -> None:
        response = self.client.post("/api/upload", data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("archivo", response.get_json()["error"])

    def test_upload_rejects_empty_file(self) -> None:
        response = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b""), "empty.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("vacío", response.get_json()["error"])
        self.assertEqual(list(self.upload_dir.iterdir()), [])

    def test_upload_rejects_invalid_filename(self) -> None:
        response = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b"payload"), "../../")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(self.upload_dir.iterdir()), [])

    def test_upload_rejects_file_over_configured_limit(self) -> None:
        response = self.client.post(
            "/api/upload",
            data={
                "file": (
                    io.BytesIO(b"x" * (1024 * 1024 + 1)),
                    "large.pdf",
                )
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 413)
        self.assertIn("1 MB", response.get_json()["error"])
        self.assertEqual(list(self.upload_dir.iterdir()), [])

    def test_tunnel_access_key_protects_page_and_upload(self) -> None:
        self.app.config["ACCESS_TOKEN"] = "test-secret"
        self.assertEqual(self.client.get("/").status_code, 403)
        page = self.client.get("/?key=test-secret")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"test-secret", page.data)

        denied = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b"payload"), "secret.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(denied.status_code, 403)
        accepted = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b"payload"), "secret.pdf")},
            headers={"X-DocInBox-Key": "test-secret"},
            content_type="multipart/form-data",
        )
        self.assertEqual(accepted.status_code, 201)


if __name__ == "__main__":
    unittest.main()
