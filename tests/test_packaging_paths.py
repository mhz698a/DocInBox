from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config


class FrozenResourcePathTests(unittest.TestCase):
    def test_frozen_app_uses_pyinstaller_bundle_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_directory = Path(temporary_directory) / "_internal"
            bundle_directory.mkdir()

            with (
                patch.object(config.sys, "frozen", True, create=True),
                patch.object(
                    config.sys,
                    "_MEIPASS",
                    str(bundle_directory),
                    create=True,
                ),
            ):
                self.assertEqual(
                    Path(config.get_program_path()),
                    bundle_directory.resolve(),
                )

    def test_source_app_uses_project_directory(self) -> None:
        with patch.object(config.sys, "frozen", False, create=True):
            self.assertEqual(
                Path(config.get_program_path()),
                Path(config.__file__).resolve().parent,
            )


if __name__ == "__main__":
    unittest.main()
