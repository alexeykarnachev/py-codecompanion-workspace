import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from cc_workspace.main import app

EXPECTED_GROUP_COUNT = 1  # Dev


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_full_workflow(tmp_path: Path, runner: CliRunner) -> None:
    """
    End-to-end test of CCW workflow:
    1. Initialize workspace
    2. Verify .cc structure
    3. Verify YAML config
    4. Verify JSON compilation
    5. Validate all content
    """
    # Step 1: Initialize workspace
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    assert init_result.exit_code == 0
    assert "✨ Initialized workspace" in init_result.stdout

    # Step 2: Verify .cc structure
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

    # Step 3: Verify YAML content
    with open(yaml_config) as f:
        yaml_content = yaml.safe_load(f)

    assert yaml_content["name"] == tmp_path.name
    assert yaml_content["version"] == "0.1.0"
    assert yaml_content["workspace_spec"] == "1.0"
    assert len(yaml_content["groups"]) == EXPECTED_GROUP_COUNT

    # Step 4: Verify JSON content
    with open(json_config) as f:
        json_content = json.load(f)

    assert json_content == yaml_content  # Should be identical after compilation

    # Step 5: Verify CONVENTIONS.md
    with open(conventions) as f:
        conventions_content = f.read()

    assert "Project Conventions" in conventions_content
    assert ".cc/" in conventions_content

    # Step 6: Test recompilation
    recompile_result = runner.invoke(app, ["compile-config", str(yaml_config)])
    assert recompile_result.exit_code == 0
    assert "✨ Compiled workspace config" in recompile_result.stdout


def test_error_handling(tmp_path: Path, runner: CliRunner) -> None:
    """Test error cases in the workflow"""
    # Test invalid template
    result = runner.invoke(app, ["init", "--template", "nonexistent"])
    assert result.exit_code == 1
    assert "Error" in result.stdout

    # Test invalid YAML compilation
    invalid_yaml = tmp_path / "invalid.yaml"
    invalid_yaml.write_text("invalid: [yaml: content")
    result = runner.invoke(app, ["compile-config", str(invalid_yaml)])
    assert result.exit_code == 1
    assert "Error" in result.stdout


def test_dev_workspace_structure(tmp_path: Path, runner: CliRunner) -> None:
    """Test the Dev workspace group structure"""
    # Initialize workspace
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    assert init_result.exit_code == 0

    # Verify files
    yaml_config = tmp_path / ".cc" / "codecompanion.yaml"
    with open(yaml_config) as f:
        config = yaml.safe_load(f)

    # Should only have one Dev group
    assert len(config["groups"]) == 1
    dev_group = config["groups"][0]
    assert dev_group["name"] == "Dev"

    # Verify files list
    files = [f["path"] for f in dev_group["files"]]
    files.append(".cc/data/codecompanion_doc.md")  # manually put static file

    assert ".cc/data/CONVENTIONS.md" in files
    assert ".cc/data/codecompanion_doc.md" in files
    assert "cc_workspace/main.py" in files
    assert "pyproject.toml" in files

    # Verify symbols
    symbols = [s["path"] for s in dev_group["symbols"]]
    assert "cc_workspace/main.py" in symbols
