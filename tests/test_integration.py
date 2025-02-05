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
    # Initialize workspace
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    assert init_result.exit_code == 0
    assert "✨ Initialized workspace" in init_result.stdout

    # Verify structure
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
    assert yaml_content["groups"][0]["name"] == "Main"

    # Verify JSON content
    with open(json_config) as f:
        json_content = json.load(f)

    assert json_content["name"] == yaml_content["name"]
    assert json_content["groups"] == yaml_content["groups"]

    # Verify CONVENTIONS.md
    with open(conventions) as f:
        conventions_content = f.read()

    assert "Project Conventions" in conventions_content
    assert "Package Management" in conventions_content


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


def test_dev_workspace_structure(tmp_path: Path, runner: CliRunner) -> None:
    """Test the workspace structure with package files"""
    # Initialize workspace
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    print(f"Init output: {init_result.stdout}")
    assert init_result.exit_code == 0

    # Verify files
    yaml_config = tmp_path / ".cc" / "codecompanion.yaml"
    with open(yaml_config) as f:
        config = yaml.safe_load(f)

    # Should have one group
    assert len(config["groups"]) == 1
    main_group = config["groups"][0]
    assert main_group["name"] == "Main"

    # Verify default files are created
    data_dir = tmp_path / ".cc" / "data"
    assert (data_dir / "CONVENTIONS.md").exists()
    assert (data_dir / "codecompanion_doc.md").exists()
