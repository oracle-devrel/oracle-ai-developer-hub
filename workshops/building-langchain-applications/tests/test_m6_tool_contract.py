"""Contract tests for the notebook's bounded weather tool."""

import contextlib
import io
import json
import unittest
from pathlib import Path

from pydantic import ValidationError

NOTEBOOK = Path(__file__).parents[1] / "notebooks/01_oracle_rag_and_memory.ipynb"


class M6ToolContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cell = next(
            cell for cell in notebook["cells"] if cell.get("id") == "weather-tool-definition"
        )
        namespace = {"json": json}
        with contextlib.redirect_stdout(io.StringIO()):
            exec("".join(cell["source"]), namespace)
        cls.namespace = namespace

    def setUp(self):
        self.tool = self.namespace["get_paris_weather"]
        self.namespace["WEATHER_ENDPOINT"] = "http://127.0.0.1:1/forecast"

    def test_tool_schema_is_typed_and_bounded(self):
        self.assertEqual(self.tool.args["units"]["enum"], ["celsius", "fahrenheit"])
        self.assertEqual(self.tool.args["forecast"]["type"], "boolean")
        self.assertIn("current weather", self.tool.description.lower())

    def test_offline_failure_is_explicitly_labeled(self):
        result = self.tool.invoke({"units": "celsius", "forecast": False})
        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["source_url"], "offline://paris-weather-fixture")
        self.assertTrue(result["uncertainty"])

    def test_invalid_units_are_rejected_by_the_tool_schema(self):
        with self.assertRaises(ValidationError):
            self.tool.invoke({"units": "kelvin", "forecast": False})


if __name__ == "__main__":
    unittest.main()
