"""Read-only prerequisites check for the Oracle RAG and memory tutorial.

This command does not pull images, start containers, connect to Oracle, or verify
the image digest. The recorded database startup and OracleVS round-trip remain in
``M1_VALIDATION.md`` and the opt-in integration test.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

IMAGE = "container-registry.oracle.com/database/free:23.26.2.0-lite-amd64"


def check(label: str, passed: bool, detail: str) -> bool:
    print(f"{'PASS' if passed else 'FAIL'}  {label}: {detail}")
    return passed


def run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-image",
        action="store_true",
        help="fail unless the pinned Oracle Free Lite image tag is available locally",
    )
    args = parser.parse_args()

    results = [
        check("Python", sys.version_info >= (3, 11), sys.version.split()[0]),
        check("Docker CLI", shutil.which("docker") is not None, "docker found"),
    ]

    docker_version = (
        run("docker", "version", "--format", "{{.Server.Version}}")
        if shutil.which("docker")
        else None
    )
    results.append(
        check(
            "Docker daemon",
            docker_version is not None and docker_version.returncode == 0,
            (docker_version.stdout.strip() or docker_version.stderr.strip())
            if docker_version
            else "docker CLI unavailable",
        )
    )

    if args.require_image:
        image = run("docker", "image", "inspect", IMAGE, "--format", "{{.Id}}")
        results.append(
            check(
                "Pinned Oracle image",
                image.returncode == 0,
                image.stdout.strip() if image.returncode == 0 else "not present locally",
            )
        )

    for variable in ("ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN"):
        # Presence only: preflight never prints secrets.
        results.append(
            check(
                variable,
                bool(os.environ.get(variable)),
                "set" if os.environ.get(variable) else "missing",
            )
        )

    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
