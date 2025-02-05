from pathlib import Path

import pytest
from typer.testing import CliRunner

from cc_workspace.main import FilePattern, FileRef, Group, app


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


def test_pattern_resolution(tmp_path: Path) -> None:
    """Test pattern-based file discovery"""
    # Create test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("# Main module")
    (tmp_path / "src/utils.py").write_text("# Utils module")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_main.py").write_text("# Tests")
    (tmp_path / "README.md").write_text("# Readme")

    # Create group with patterns
    group = Group(
        name="Test",
        description="Test group",
        files=[
            FilePattern(pattern="src/**/*.py", description="Source file"),
            FilePattern(pattern="**/*.md", description="Doc file"),
            FileRef(path="tests/test_main.py", description="Test file"),
        ],
    )

    # Resolve patterns
    group.resolve_patterns(tmp_path)
    resolved = group.get_files()

    # Verify results
    assert len(resolved) == 4
    paths = {f.path for f in resolved}
    assert paths == {"src/main.py", "src/utils.py", "README.md", "tests/test_main.py"}


def test_pattern_resolution_empty(tmp_path: Path) -> None:
    """Test pattern resolution with no matching files"""
    group = Group(
        name="Empty",
        description="Empty group",
        files=[
            FilePattern(pattern="nonexistent/*.py", description="No files"),
        ],
    )

    group.resolve_patterns(tmp_path)
    resolved = group.get_files()
    assert len(resolved) == 0


def test_mixed_patterns_and_refs(tmp_path: Path) -> None:
    """Test mixing patterns and explicit refs"""
    # Create test file
    (tmp_path / "config.yaml").write_text("config: true")

    group = Group(
        name="Mixed",
        description="Mixed group",
        files=[
            FilePattern(pattern="*.yaml", description="Config file"),
            FileRef(path="config.yaml", description="Explicit config"),
        ],
    )

    group.resolve_patterns(tmp_path)
    resolved = group.get_files()

    # Should have both pattern-matched and explicit file
    assert len(resolved) == 2
    assert all(f.path == "config.yaml" for f in resolved)


def test_unresolved_files_error() -> None:
    """Test error when accessing files before resolution"""
    group = Group(
        name="Test", description="Test group", files=[FilePattern(pattern="*.py")]
    )

    with pytest.raises(ValueError, match="Files not resolved"):
        group.get_files()


def test_dev_template_patterns(tmp_path: Path, runner: CliRunner) -> None:
    """Test the dev template with pattern-based discovery"""
    # Create some test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("# Main")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_main.py").write_text("# Test")
    (tmp_path / "README.md").write_text("# Doc")

    # Initialize with dev template
    result = runner.invoke(app, ["init", str(tmp_path), "--template", "dev"])
    assert result.exit_code == 0

    # Verify JSON output
    json_path = tmp_path / "codecompanion-workspace.json"
    assert json_path.exists()
