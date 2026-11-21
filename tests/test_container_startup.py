import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts import start_container


@pytest.fixture
def container_startup(monkeypatch, tmp_path):
    monkeypatch.setattr(start_container.settings, "database_path", tmp_path / "data" / "app.sqlite3")
    monkeypatch.setattr(start_container.settings, "media_root", tmp_path / "data" / "media")
    # Include Docker's actual CMD: it used to override the entrypoint's default port.
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text()
    command = next(line[4:] for line in dockerfile.splitlines() if line.startswith("CMD "))
    monkeypatch.setattr(start_container.sys, "argv", ["start_container", *json.loads(command)])
    migrate = Mock()
    execute = Mock()
    monkeypatch.setattr(start_container.subprocess, "run", migrate)
    monkeypatch.setattr(start_container.os, "execvp", execute)
    return migrate, execute


@pytest.mark.parametrize("port,expected", [("80", "80"), ("32100", "32100"), (None, "8000")])
def test_container_listens_on_host_port(monkeypatch, container_startup, port, expected):
    if port is None:
        monkeypatch.delenv("PORT", raising=False)
    else:
        monkeypatch.setenv("PORT", port)

    migrate, execute = container_startup
    start_container.main()

    migrate.assert_called_once()
    execute.assert_called_once()
    command = execute.call_args.args[1]
    assert command[command.index("--port") + 1] == expected
    assert command[command.index("--host") + 1] == "0.0.0.0"


def test_failed_migration_does_not_start_server(container_startup):
    migrate, execute = container_startup
    migrate.side_effect = subprocess.CalledProcessError(1, "alembic")
    with pytest.raises(subprocess.CalledProcessError):
        start_container.main()
    execute.assert_not_called()
