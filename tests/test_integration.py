import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cc_workspace.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_workspace_structure(tmp_path: Path, runner: CliRunner) -> None:
    """Test the basic workspace structure and file discovery"""
    # Create test structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("print('hello')")
    (tmp_path / "README.md").write_text("# Documentation")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules/package.json").write_text("{}")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git/config").write_text("git config")

    # Initialize workspace
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "✨ Initialized workspace" in result.stdout

    # Verify JSON content and structure
    json_config = tmp_path / "codecompanion-workspace.json"
    assert json_config.exists()

    with open(json_config) as f:
        json_content = json.load(f)

    # Verify required fields
    assert "name" in json_content
    assert "system_prompt" in json_content
    assert "groups" in json_content
    assert isinstance(json_content["groups"], list)

    # Verify ignore section is not present
    assert "ignore" not in json_content

    # Check file discovery still works
    files = {f["path"] for g in json_content["groups"] for f in g["files"]}
    assert "src/main.py" in files  # Should include regular files
    assert "README.md" in files  # Should include docs
    assert ".cc/data/CONVENTIONS.md" in files  # Should include conventions
    assert "node_modules/package.json" not in files  # Should respect ignores
    assert ".git/config" not in files  # Should ignore dot directories


def test_error_handling(tmp_path: Path, runner: CliRunner) -> None:
    # Test invalid template
    result = runner.invoke(app, ["init", "--template", "nonexistent"])
    assert result.exit_code == 1
    assert "Template 'nonexistent' not found" in result.stdout

    # Test invalid YAML compilation
    invalid_yaml = tmp_path / "invalid.yaml"
    invalid_yaml.write_text("invalid: [yaml: content")
    result = runner.invoke(app, ["compile-config", str(invalid_yaml)])
    assert result.exit_code == 1
    assert "Error" in result.stdout


def test_json_structure_consistency(tmp_path: Path, runner: CliRunner) -> None:
    """Test that JSON output maintains consistent structure across operations"""
    # Initialize workspace
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    assert init_result.exit_code == 0

    # Get initial JSON structure
    json_path = tmp_path / "codecompanion-workspace.json"
    with open(json_path) as f:
        initial_data = json.load(f)

    # Verify structure after compilation
    yaml_path = tmp_path / ".cc" / "codecompanion.yaml"
    compile_result = runner.invoke(app, ["compile-config", str(yaml_path)])
    assert compile_result.exit_code == 0

    with open(json_path) as f:
        compiled_data = json.load(f)

    # Check structure consistency
    assert set(initial_data.keys()) == set(compiled_data.keys())
    assert "ignore" not in initial_data
    assert "ignore" not in compiled_data

    # Verify group structure
    for group in compiled_data["groups"]:
        assert set(group.keys()) <= {
            "name",
            "description",
            "system_prompt",
            "files",
            "symbols",
        }
