import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cc_workspace.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def is_git_command(cmd: list[str], *args: str) -> bool:
    """Check if command matches Git command pattern"""
    return cmd[0] == "git" and cmd[1:] == list(args)


GIT_INIT_CMD = ["init", "--quiet"]
GIT_ADD_CMD = ["add", "."]
GIT_COMMIT_CMD = ["commit", "--quiet", "-m", "Initial commit ✨"]
GIT_VERSION_CMD = ["--version"]
GIT_USERNAME_CMD = ["config", "user.name"]


def create_mock_subprocess() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Create a mock subprocess function that handles all Git commands"""

    def mock_subprocess(*args: Any, **_: Any) -> subprocess.CompletedProcess[str]:
        cmd = args[0]
        if not isinstance(cmd, list) or not cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        if is_git_command(cmd, *GIT_VERSION_CMD):
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="git version 2.34.1"
            )

        if is_git_command(cmd, *GIT_USERNAME_CMD):
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="Test User\n"
            )

        if any(
            is_git_command(cmd, *git_cmd)
            for git_cmd in [GIT_INIT_CMD, GIT_ADD_CMD, GIT_COMMIT_CMD]
        ):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

    return mock_subprocess


def create_mock_subprocess_with_username(
    username: str,
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Create a mock subprocess with specific username"""

    def mock_subprocess(*args: Any, **_: Any) -> subprocess.CompletedProcess[str]:
        cmd = args[0]
        if not isinstance(cmd, list) or not cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        if is_git_command(cmd, *GIT_VERSION_CMD):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        if is_git_command(cmd, *GIT_USERNAME_CMD):
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=f"{username}\n"
            )

        if any(
            is_git_command(cmd, *git_cmd)
            for git_cmd in [GIT_INIT_CMD, GIT_ADD_CMD, GIT_COMMIT_CMD]
        ):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

    return mock_subprocess


def create_mock_subprocess_with_error() -> (
    Callable[..., subprocess.CompletedProcess[str]]
):
    """Create a mock subprocess that simulates Git config error"""

    def mock_subprocess(*args: Any, **_: Any) -> subprocess.CompletedProcess[str]:
        cmd = args[0]
        if not isinstance(cmd, list) or not cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        if is_git_command(cmd, *GIT_VERSION_CMD):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        if is_git_command(cmd, *GIT_USERNAME_CMD):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

        if any(
            is_git_command(cmd, *git_cmd)
            for git_cmd in [GIT_INIT_CMD, GIT_ADD_CMD, GIT_COMMIT_CMD]
        ):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

    return mock_subprocess


def test_error_handling(tmp_path: Path, runner: CliRunner) -> None:
    """Test error handling for invalid inputs"""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Test invalid template
        result = runner.invoke(app, ["init", "--template", "nonexistent"])
        assert result.exit_code == 1
        assert "Template 'nonexistent' not found" in result.stdout


def test_init_new_project_structure(tmp_path: Path, runner: CliRunner) -> None:
    """Test basic project structure creation"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess()
        result = runner.invoke(app, ["init", "test-proj"])
        assert result.exit_code == 0

        project_path = Path(fs) / "test-proj"
        assert project_path.exists()

        # Check package structure
        pkg_path = project_path / "test_proj"
        assert pkg_path.exists()
        assert (pkg_path / "__init__.py").exists()
        assert (pkg_path / "main.py").exists()

        # Check package name conversion
        init_content = (pkg_path / "__init__.py").read_text()
        assert '__version__ = "0.1.0"' in init_content


def test_init_new_project_tests(tmp_path: Path, runner: CliRunner) -> None:
    """Test test directory structure and content"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess()
        result = runner.invoke(app, ["init", "test-proj"])
        assert result.exit_code == 0

        project_path = Path(fs) / "test-proj"

        # Check test structure
        test_path = project_path / "tests"
        assert test_path.exists()
        assert (test_path / "__init__.py").exists()
        assert (test_path / "test_basic.py").exists()

        # Check test content
        test_content = (test_path / "test_basic.py").read_text()
        assert "import test_proj" in test_content
        assert "test_proj.__version__" in test_content


def test_init_new_project_scripts(tmp_path: Path, runner: CliRunner) -> None:
    """Test scripts creation and content"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess()
        result = runner.invoke(app, ["init", "test-proj"])
        assert result.exit_code == 0

        project_path = Path(fs) / "test-proj"

        # Check ccw_check.sh script
        script_path = project_path / "scripts" / "ccw_check.sh"
        assert script_path.exists()
        assert script_path.stat().st_mode & 0o111  # Check if executable
        script_content = script_path.read_text()
        assert "Running complete verification" in script_content
        assert "ruff check" in script_content
        assert "mypy --strict" in script_content
        assert "pytest -v tests/" in script_content


def test_init_new_project_config(tmp_path: Path, runner: CliRunner) -> None:
    """Test project configuration files"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess()
        result = runner.invoke(app, ["init", "test-proj"])
        assert result.exit_code == 0

        project_path = Path(fs) / "test-proj"

        # Check pyproject.toml
        pyproject_path = project_path / "pyproject.toml"
        assert pyproject_path.exists()
        pyproject_content = pyproject_path.read_text()
        assert 'name = "test_proj"' in pyproject_content
        assert 'path = "test_proj/__init__.py"' in pyproject_content
        assert "requires-python = " in pyproject_content
        assert "[tool.pytest.ini_options]" in pyproject_content
        assert "[tool.ruff.lint]" in pyproject_content


def test_init_new_project_docs(tmp_path: Path, runner: CliRunner) -> None:
    """Test documentation files creation and content"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess()
        result = runner.invoke(app, ["init", "test-proj"])
        assert result.exit_code == 0

        project_path = Path(fs) / "test-proj"

        # Check documentation files
        assert (project_path / "README.md").exists()
        assert (project_path / "CHANGELOG.md").exists()
        assert (project_path / ".gitignore").exists()

        # Verify documentation content
        readme_content = (project_path / "README.md").read_text()
        assert "test_proj" in readme_content
        assert "Quick Start" in readme_content

        changelog_content = (project_path / "CHANGELOG.md").read_text()
        assert "Changelog" in changelog_content
        assert "Keep a Changelog" in changelog_content

        gitignore_content = (project_path / ".gitignore").read_text()
        assert "__pycache__" in gitignore_content
        assert ".cc/" in gitignore_content


def test_git_initialization(tmp_path: Path, runner: CliRunner) -> None:
    """Test Git initialization behavior"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess()
        result = runner.invoke(app, ["init", "test-proj"])
        assert result.exit_code == 0
        project_path = Path(fs) / "test-proj"
        assert project_path.exists()

        # Verify Git commands were called in correct order
        git_commands = [
            args[0] for args, _ in mock_run.call_args_list if args[0][0] == "git"
        ]
        assert ["git", "--version"] in git_commands
        assert ["git", "init", "--quiet"] in git_commands
        assert ["git", "add", "."] in git_commands
        assert ["git", "commit", "--quiet", "-m", "Initial commit ✨"] in git_commands


def test_init_current_directory(tmp_path: Path, runner: CliRunner) -> None:
    """Test initializing in current directory"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess()
        # Should not prompt for confirmation in current directory
        result = runner.invoke(app, ["init", "."])
        assert result.exit_code == 0
        assert (Path(fs) / ".cc").exists()
        assert (Path(fs) / "codecompanion-workspace.json").exists()
        assert "Initialized workspace in current directory" in result.stdout


def test_init_existing_directory(tmp_path: Path, runner: CliRunner) -> None:
    """Test initialization in existing directory"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess()
        # Create existing project
        project_path = Path(fs) / "existing-proj"
        project_path.mkdir()
        (project_path / "existing.txt").write_text("existing content")

        # Creating new project should prompt
        result = runner.invoke(app, ["init", "existing-proj"], input="n\n")
        assert result.exit_code == 0
        assert "Initialize anyway?" in result.stdout
        assert not (project_path / ".cc").exists()

        # Force flag should skip prompt
        result = runner.invoke(app, ["init", "existing-proj", "--force"])
        assert result.exit_code == 0
        assert (project_path / ".cc").exists()
        assert (project_path / "codecompanion-workspace.json").exists()


def test_workspace_structure(tmp_path: Path, runner: CliRunner) -> None:
    """Test the basic workspace structure and file discovery"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess()
        # Create test structure
        test_dir = Path(fs)
        (test_dir / "src").mkdir()
        (test_dir / "src/main.py").write_text("print('hello')")
        (test_dir / "README.md").write_text("# Documentation")
        (test_dir / "node_modules").mkdir()
        (test_dir / "node_modules/package.json").write_text("{}")
        (test_dir / ".git").mkdir()
        (test_dir / ".git/config").write_text("git config")

        # Initialize workspace in existing directory
        result = runner.invoke(app, ["init", "."])
        assert result.exit_code == 0

        # Verify JSON content and structure
        json_config = test_dir / "codecompanion-workspace.json"
        assert json_config.exists()

        with open(json_config) as f:
            json_content = json.load(f)

        # Verify required fields
        assert "name" in json_content
        assert "system_prompt" in json_content
        assert "groups" in json_content
        assert isinstance(json_content["groups"], list)

        # Check file discovery
        files = {f["path"] for g in json_content["groups"] for f in g["files"]}
        assert "src/main.py" in files  # Should include regular files
        assert "README.md" in files  # Should include docs
        assert ".cc/data/CONVENTIONS.md" in files  # Should include conventions
        assert "node_modules/package.json" not in files  # Should respect ignores
        assert ".git/config" not in files  # Should ignore dot directories


def test_project_name_conversion(tmp_path: Path, runner: CliRunner) -> None:
    """Test project name conversion to package name"""
    test_cases = [
        ("my-project", "my_project"),
        ("My.Project", "my_project"),
        ("MY_PROJECT", "my_project"),
        ("my.cool-project", "my_cool_project"),
    ]

    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess()
        for project_name, package_name in test_cases:
            result = runner.invoke(app, ["init", project_name])
            assert result.exit_code == 0

            project_path = Path(fs) / project_name
            pkg_path = project_path / package_name
            assert pkg_path.exists()

            # Check package imports correctly
            test_content = (project_path / "tests/test_basic.py").read_text()
            assert f"import {package_name}" in test_content


def test_git_username_extraction(tmp_path: Path, runner: CliRunner) -> None:
    """Test Git username extraction and fallback behavior"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess_with_username("John Doe")
        result = runner.invoke(app, ["init", "test-proj"])
        assert result.exit_code == 0

        pyproject_path = Path(fs) / "test-proj" / "pyproject.toml"
        content = pyproject_path.read_text()
        assert 'homepage = "https://github.com/johndoe/test_proj"' in content
        assert 'repository = "https://github.com/johndoe/test_proj"' in content


def test_git_username_special_chars(tmp_path: Path, runner: CliRunner) -> None:
    """Test handling of special characters in Git username"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess_with_username(
            "John Smith-Doe Jr."
        )
        result = runner.invoke(app, ["init", "test-proj"])
        assert result.exit_code == 0

        pyproject_path = Path(fs) / "test-proj" / "pyproject.toml"
        content = pyproject_path.read_text()
        assert 'homepage = "https://github.com/johnsmithdoejr/test_proj"' in content
        assert 'repository = "https://github.com/johnsmithdoejr/test_proj"' in content


def test_git_username_error_handling(tmp_path: Path, runner: CliRunner) -> None:
    """Test handling of Git config errors"""
    with (
        runner.isolated_filesystem(temp_dir=tmp_path) as fs,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = create_mock_subprocess_with_error()
        result = runner.invoke(app, ["init", "test-proj"])
        assert result.exit_code == 0

        pyproject_path = Path(fs) / "test-proj" / "pyproject.toml"
        content = pyproject_path.read_text()
        assert 'homepage = "https://github.com/username/test_proj"' in content
        assert 'repository = "https://github.com/username/test_proj"' in content
