from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from subprocess import CompletedProcess
from unittest.mock import patch

from scripts import preflight


def completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> CompletedProcess[str]:
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class PreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = {
            "ORACLE_USER": "RAG_APP",
            "ORACLE_PASSWORD": "a-secret-that-must-not-be-printed",
            "ORACLE_DSN": "localhost:1521/FREEPDB1",
        }

    def run_main(
        self, arguments: list[str], *command_results: CompletedProcess[str]
    ) -> tuple[int, str]:
        output = io.StringIO()
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(sys, "argv", ["preflight.py", *arguments]),
            patch("scripts.preflight.shutil.which", return_value="/usr/bin/docker"),
            patch("scripts.preflight.run", side_effect=command_results),
            redirect_stdout(output),
        ):
            result = preflight.main()
        return result, output.getvalue()

    def test_success_does_not_print_secret(self) -> None:
        result, output = self.run_main([], completed(stdout="26.1.0"))
        self.assertEqual(result, 0)
        self.assertIn("PASS  Docker daemon", output)
        self.assertNotIn(self.environment["ORACLE_PASSWORD"], output)

    def test_missing_environment_variable_fails_without_printing_secret(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(
                os.environ,
                {"ORACLE_USER": "RAG_APP", "ORACLE_DSN": self.environment["ORACLE_DSN"]},
                clear=True,
            ),
            patch.object(sys, "argv", ["preflight.py"]),
            patch("scripts.preflight.shutil.which", return_value="/usr/bin/docker"),
            patch("scripts.preflight.run", return_value=completed(stdout="26.1.0")),
            redirect_stdout(output),
        ):
            result = preflight.main()
        self.assertEqual(result, 1)
        self.assertIn("FAIL  ORACLE_PASSWORD: missing", output.getvalue())
        self.assertNotIn(self.environment["ORACLE_PASSWORD"], output.getvalue())

    def test_missing_docker_cli_fails_without_running_docker(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(sys, "argv", ["preflight.py"]),
            patch("scripts.preflight.shutil.which", return_value=None),
            patch("scripts.preflight.run") as docker_run,
            redirect_stdout(output),
        ):
            result = preflight.main()
        self.assertEqual(result, 1)
        self.assertIn("FAIL  Docker CLI", output.getvalue())
        docker_run.assert_not_called()

    def test_unavailable_docker_daemon_fails(self) -> None:
        result, output = self.run_main([], completed(returncode=1, stderr="daemon unavailable"))
        self.assertEqual(result, 1)
        self.assertIn("FAIL  Docker daemon: daemon unavailable", output)

    def test_require_image_checks_pinned_image(self) -> None:
        result, output = self.run_main(
            ["--require-image"],
            completed(stdout="26.1.0"),
            completed(stdout="sha256:pinned"),
        )
        self.assertEqual(result, 0)
        self.assertIn("PASS  Pinned Oracle image: sha256:pinned", output)

        result, output = self.run_main(
            ["--require-image"],
            completed(stdout="26.1.0"),
            completed(returncode=1),
        )
        self.assertEqual(result, 1)
        self.assertIn("FAIL  Pinned Oracle image: not present locally", output)

    def test_old_python_version_fails(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(sys, "argv", ["preflight.py"]),
            patch.object(sys, "version_info", (3, 10)),
            patch.object(sys, "version", "3.10.0"),
            patch("scripts.preflight.shutil.which", return_value="/usr/bin/docker"),
            patch("scripts.preflight.run", return_value=completed(stdout="26.1.0")),
            redirect_stdout(output),
        ):
            result = preflight.main()
        self.assertEqual(result, 1)
        self.assertIn("FAIL  Python: 3.10.0", output.getvalue())


if __name__ == "__main__":
    unittest.main()
