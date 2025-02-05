from pathlib import Path

import pytest
from typer.testing import CliRunner

from cc_workspace.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_init_command(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "✨ Initialized workspace" in result.stdout
    assert (tmp_path / ".cc" / "codecompanion.yaml").exists()
    assert (tmp_path / "codecompanion-workspace.json").exists()


def test_compile_config_command(tmp_path: Path, runner: CliRunner) -> None:
    # First init
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    assert init_result.exit_code == 0

    # Then compile config
    yaml_path = tmp_path / ".cc" / "codecompanion.yaml"
    result = runner.invoke(app, ["compile-config", str(yaml_path)])
    assert result.exit_code == 0
    assert "✨ Compiled workspace config" in result.stdout
    assert (tmp_path / "codecompanion-workspace.json").exists()


def test_cli_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout


def test_init_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout


def test_file_validation(tmp_path: Path, runner: CliRunner) -> None:
    yaml_content = """
name: test
description: Test workspace
groups:
  - name: Test
    files:
      - path: nonexistent.py
    symbols:
      - path: also_missing.py
"""
    config_path = tmp_path / "test.yaml"
    config_path.write_text(yaml_content)

    result = runner.invoke(app, ["compile-config", str(config_path)])
    assert result.exit_code == 1
    assert "Invalid workspace:" in result.stdout
    assert "File not found: nonexistent.py" in result.stdout
    assert "Symbol file not found: also_missing.py" in result.stdout


def test_progress_display(tmp_path: Path, runner: CliRunner) -> None:
    """Test progress indication during compilation"""
    # First init to create valid files
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    assert init_result.exit_code == 0

    # Then test compilation output
    yaml_path = tmp_path / ".cc" / "codecompanion.yaml"
    result = runner.invoke(app, ["compile-config", str(yaml_path)])
    assert result.exit_code == 0

    # Verify progress messages
    assert "Reading config" in result.stdout
    assert "Validating schema" in result.stdout
    assert "Checking files" in result.stdout
    assert "Writing output" in result.stdout
