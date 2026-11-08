from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import fitz

from services.qr_pdf import generate_qr_pdf


class QrPdfTests(unittest.TestCase):
    def test_creates_one_page_printable_pdf_with_url_and_vector_qr(self) -> None:
        url = "https://receive-123.tunnelmole.net/?key=secret-token-value"
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "access-qr.pdf"
            result = generate_qr_pdf(url, output)

            self.assertEqual(result, output.resolve())
            self.assertTrue(output.is_file())
            with fitz.open(output) as document:
                self.assertEqual(len(document), 1)
                page = document[0]
                text = page.get_text()
                self.assertIn("DocInBox", text)
                self.assertIn(url, text)
                drawing_items = sum(
                    len(drawing["items"]) for drawing in page.get_drawings()
                )
                self.assertGreater(drawing_items, 100)

    def test_rejects_empty_or_non_https_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "access.pdf"
            with self.assertRaises(ValueError):
                generate_qr_pdf("", output)
            with self.assertRaises(ValueError):
                generate_qr_pdf("http://127.0.0.1:8765", output)
            self.assertFalse(output.exists())

    def test_requires_pdf_extension(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "access.png"
            with self.assertRaisesRegex(ValueError, "pdf"):
                generate_qr_pdf("https://receive.tunnelmole.net", output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
