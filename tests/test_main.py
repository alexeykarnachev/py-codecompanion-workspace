from pathlib import Path

from typer.testing import CliRunner

from cc_workspace.main import app

runner = CliRunner()


def test_init_command(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "✨ Initialized workspace" in result.stdout
    assert (tmp_path / ".cc" / "codecompanion.yaml").exists()


def test_compile_config_command(tmp_path: Path) -> None:
    """Test the compile-config command workflow"""
    # First init
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    assert init_result.exit_code == 0

    # Then compile config
    yaml_path = tmp_path / ".cc" / "codecompanion.yaml"
    result = runner.invoke(app, ["compile-config", str(yaml_path)])
    assert result.exit_code == 0
    assert "✨ Compiled workspace config" in result.stdout
    assert (tmp_path / "codecompanion-workspace.json").exists()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout


def test_init_help() -> None:
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
