from __future__ import annotations

import unittest
from pathlib import Path

import nbformat

NOTEBOOK = Path(__file__).parents[1] / "notebooks/01_oracle_rag_and_memory.ipynb"


class MemoryNotebookContractTest(unittest.TestCase):
    def load_notebook(self):
        return nbformat.read(NOTEBOOK, as_version=4)

    def test_every_memory_search_is_exactly_user_scoped(self) -> None:
        notebook = self.load_notebook()
        search_cells = [
            cell.source
            for cell in notebook.cells
            if cell.cell_type == "code"
            and ("memory.search(" in cell.source or "memory.search_async(" in cell.source)
        ]

        self.assertGreaterEqual(len(search_cells), 4)
        for source in search_cells:
            self.assertIn("user_id=", source)
            self.assertIn("exact_user_match=True", source)

    def test_explicit_memory_write_records_provenance_and_timestamp(self) -> None:
        notebook = self.load_notebook()
        write_cells = [
            cell.source
            for cell in notebook.cells
            if cell.cell_type == "code" and "thread.add_memory" in cell.source
        ]

        self.assertGreaterEqual(len(write_cells), 1)
        timestamped_write = next(
            source for source in write_cells if "preference_timestamp" in source
        )
        self.assertIn("thread.add_memory_async(", timestamped_write)
        self.assertIn("timestamp=preference_timestamp", timestamped_write)
        self.assertIn("explicit_user_statement", timestamped_write)


if __name__ == "__main__":
    unittest.main()
