from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from app_flask import create_app


class ReceiverApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_dir = Path(self.temp_dir.name) / "received"
        self.app = create_app(
            {
                "TESTING": True,
                "UPLOAD_FOLDER": self.upload_dir,
                "MAX_CONTENT_LENGTH": 2 * 1024 * 1024,
                "MAX_UPLOAD_BYTES": 1024 * 1024,
                "MAX_UPLOAD_MB": 1,
            }
        )
        self.client = self.app.test_client()

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
        self.assertIn(b"Env\xC3\xADa tus documentos", page.data)
        self.assertEqual(script.status_code, 200)
        self.assertEqual(stylesheet.status_code, 200)

    def test_upload_saves_file_with_generated_name(self) -> None:
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
        self.assertEqual(payload["status"], "received")

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
        self.assertEqual(
            {path.read_bytes() for path in saved_files},
            {b"first", b"second"},
        )

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


if __name__ == "__main__":
    unittest.main()
