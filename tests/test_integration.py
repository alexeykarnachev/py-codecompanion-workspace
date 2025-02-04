import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from cc_workspace.main import app


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
    assert len(yaml_content["groups"]) == 3  # Documentation, Source, Tests

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
    recompile_result = runner.invoke(app, ["compile", str(yaml_config)])
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
    result = runner.invoke(app, ["compile", str(invalid_yaml)])
    assert result.exit_code == 1
    assert "Error" in result.stdout
