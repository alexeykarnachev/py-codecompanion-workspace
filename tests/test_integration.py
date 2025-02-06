import json
from pathlib import Path

import pytest
import yaml
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

    # Verify directory structure
    cc_dir = tmp_path / ".cc"
    data_dir = cc_dir / "data"
    yaml_config = cc_dir / "codecompanion.yaml"
    json_config = tmp_path / "codecompanion-workspace.json"
    conventions = data_dir / "CONVENTIONS.md"

    assert cc_dir.exists() and cc_dir.is_dir()
    assert data_dir.exists() and data_dir.is_dir()
    assert yaml_config.exists() and yaml_config.is_file()
    assert json_config.exists() and json_config.is_file()
    assert conventions.exists() and conventions.is_file()

    # Verify YAML content
    with open(yaml_config) as f:
        yaml_content = yaml.safe_load(f)

    assert yaml_content["name"] == tmp_path.name
    assert "description" in yaml_content
    assert len(yaml_content["groups"]) == 1
    assert yaml_content["groups"][0]["name"] == "Project"

    # Verify JSON content
    with open(json_config) as f:
        json_content = json.load(f)

    # Check file discovery
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
