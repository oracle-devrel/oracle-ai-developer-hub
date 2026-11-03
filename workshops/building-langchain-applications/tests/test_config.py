from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.config import load_settings


class SettingsTest(unittest.TestCase):
    def test_missing_api_key_is_reported(self) -> None:
        with patch("src.config.load_dotenv"), patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                load_settings()

    def test_settings_load_without_printing_or_transforming_secrets(self) -> None:
        values = {
            "ORACLE_USER": "TUTORIAL_USER",
            "ORACLE_PASSWORD": "not-printed",
            "ORACLE_DSN": "localhost:1521/FREEPDB1",
            "OPENAI_API_KEY": "test-key",
            "OPENAI_MODEL": "gpt-5-mini",
            "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
            "CORPUS_VERSION": "2026.1",
        }
        with patch("src.config.load_dotenv"), patch.dict(os.environ, values, clear=True):
            settings = load_settings()

        self.assertEqual(settings.oracle_user, "TUTORIAL_USER")
        self.assertEqual(settings.openai_api_key, "test-key")
        self.assertEqual(settings.openai_model, "gpt-5-mini")
        self.assertEqual(settings.embedding_model, "text-embedding-3-small")
        self.assertEqual(settings.corpus_version, "2026.1")


if __name__ == "__main__":
    unittest.main()
