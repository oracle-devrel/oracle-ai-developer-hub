"""Exercise the installer without root, network, Docker, or real credentials."""

import json
from pathlib import Path
import stat
import subprocess

from dotenv import dotenv_values
import pytest


INSTALLER = Path(__file__).resolve().parents[1] / "devcontainer-feature/oraviz-mcp/install.sh"


@pytest.fixture
def installer(tmp_path):
    install_dir = tmp_path / "server"
    remote_home = tmp_path / "home with spaces"
    remote_home.mkdir()
    script = tmp_path / "install.sh"
    script.write_text(INSTALLER.read_text().replace("/opt/oraviz-mcp", str(install_dir)))
    commands = tmp_path / "commands"
    commands.mkdir()
    # Record git arguments; a command-injection regression would execute the
    # attacker's shell payload despite this inert git implementation.
    git = commands / "git"
    git.write_text("#!/bin/bash\nprintf '%s\\n' \"$@\" >> \"$GIT_RECORD\"\n")
    git.chmod(0o755)
    chown = commands / "chown"
    chown.write_text("#!/bin/bash\nexit \"${CHOWN_EXIT:-0}\"\n")
    chown.chmod(0o755)
    env = {
        "PATH": f"{commands}:/usr/bin:/bin",
        "_REMOTE_USER": "testuser",
        "_REMOTE_USER_HOME": str(remote_home),
        "GIT_RECORD": str(tmp_path / "git-args"),
    }

    def run(**options):
        return subprocess.run(
            ["bash", str(script)], env={**env, **options}, text=True,
            capture_output=True, timeout=10, check=False,
        )

    return run, remote_home / ".oraviz-mcp-env", tmp_path


def test_credentials_are_literal_and_private(installer):
    run, env_file, tmp_path = installer
    marker = tmp_path / "executed"
    password = f"quote'\"; $(touch {marker}); `touch {marker}` \\ $TOKEN # end"
    result = run(ORACLEPASSWORD=password, ORACLEHOST="host with spaces")
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert dotenv_values(env_file)["ORACLE_PASSWORD"] == password
    assert dotenv_values(env_file)["ORACLE_HOST"] == "host with spaces"
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert password not in result.stdout + result.stderr


def test_empty_password_preserves_runtime_secret(installer):
    run, env_file, tmp_path = installer
    assert run().returncode == 0
    values = dotenv_values(env_file)
    assert values["ORACLE_USER"] == "oraviz_reader"
    assert "ORACLE_PASSWORD" not in values
    assert stat.S_IMODE((tmp_path / "server").stat().st_mode) == 0o755


@pytest.mark.parametrize("value", ["line\nbreak", "line\rbreak", "${TOKEN}"])
def test_rejects_dotenv_injection(installer, value):
    run, env_file, _ = installer
    result = run(ORACLEPASSWORD=value)
    assert result.returncode != 0
    assert not env_file.exists()
    assert value not in result.stderr


@pytest.mark.parametrize("option", ["VERSION", "ORAVIZMCPREPO", "_REMOTE_USER"])
def test_rejects_command_injection_options(installer, option):
    run, env_file, tmp_path = installer
    marker = tmp_path / "executed"
    result = run(**{option: f"value; touch {marker}"})
    assert result.returncode != 0
    assert not marker.exists()
    assert not env_file.exists()


def test_supports_pinned_source_without_shell_evaluation(installer):
    run, _, tmp_path = installer
    revision = "a" * 40
    assert run(VERSION=revision).returncode == 0
    assert (tmp_path / "git-args").read_text().splitlines() == [
        "clone", "--no-checkout", "--", "https://github.com/jasperan/oraviz-mcp", ".",
        "checkout", "--detach", revision, "--",
    ]


@pytest.mark.parametrize("symlink", [False, True])
def test_preserves_existing_file_or_symlink(installer, symlink):
    run, env_file, tmp_path = installer
    target = tmp_path / "existing"
    target.write_text("existing secret")
    if symlink:
        env_file.symlink_to(target)
    else:
        env_file.write_text("existing secret")
    result = run()
    assert result.returncode != 0
    assert env_file.read_text() == "existing secret"
    assert target.read_text() == "existing secret"


def test_ownership_failure_is_fatal_and_cleans_temporary_file(installer):
    run, env_file, _ = installer
    result = run(CHOWN_EXIT="1", ORACLEPASSWORD="synthetic-secret")
    assert result.returncode != 0
    assert not env_file.exists()
    assert list(env_file.parent.iterdir()) == []


def test_manifest_does_not_embed_password_or_admin_default():
    feature = json.loads(INSTALLER.with_name("devcontainer-feature.json").read_text())
    assert feature["options"]["oracleUser"]["default"] == "oraviz_reader"
    assert feature["options"]["oraclePassword"]["default"] == ""
