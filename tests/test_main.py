import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cc_workspace.main import File, Group, Workspace, WorkspaceIgnore, app


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

    # Verify success message instead of progress messages since they're transient
    assert "✨ Compiled workspace config" in result.stdout


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
            File(path="src/**/*.py", description="Source file", kind="pattern"),
            File(path="**/*.md", description="Doc file", kind="pattern"),
            File(path="tests/test_main.py", description="Test file", kind="file"),
        ],
    )

    # Test pattern resolution
    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}
    assert paths == {"src/main.py", "src/utils.py", "README.md", "tests/test_main.py"}


def test_pattern_resolution_empty(tmp_path: Path) -> None:
    """Test pattern resolution with no matching files"""
    group = Group(
        name="Empty",
        description="Empty group",
        files=[
            File(path="nonexistent/*.py", description="No files", kind="pattern"),
        ],
    )

    # Test pattern resolution
    resolved = group.resolve_patterns(tmp_path)
    assert len(resolved["files"]) == 0  # No files should match the pattern


def test_mixed_patterns_and_refs(tmp_path: Path) -> None:
    """Test mixing patterns and explicit refs"""
    # Create test file
    (tmp_path / "config.yaml").write_text("config: true")

    group = Group(
        name="Mixed",
        description="Mixed group",
        files=[
            File(path="*.yaml", description="Config file", kind="pattern"),
            File(path="config.yaml", description="Explicit config", kind="file"),
        ],
    )

    # Test pattern resolution
    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}
    assert paths == {"config.yaml"}  # Pattern and explicit file resolve to same path


def test_dev_template_patterns(tmp_path: Path, runner: CliRunner) -> None:
    """Test the dev template with pattern-based discovery"""
    # Debug: Check available templates
    from cc_workspace.main import TEMPLATES

    print("\nDebug template info:")
    print(f"Available templates: {TEMPLATES.list_templates()}")
    template = TEMPLATES.get("dev")
    if template:
        print(f"Dev template content:\n{template.content[:200]}")
    else:
        print("Dev template not found!")

    # Create some test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("# Main")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_main.py").write_text("# Test")
    (tmp_path / "README.md").write_text("# Doc")

    # Initialize with dev template
    result = runner.invoke(app, ["init", str(tmp_path), "--template", "dev"])
    print(f"\nCommand output:\n{result.stdout}")  # Print command output
    if result.exit_code != 0:
        print(f"Error: {result.stdout}")  # Print any error output
        print(f"Exception: {result.exception}")  # Print exception if any
    assert result.exit_code == 0

    # Verify JSON output
    json_path = tmp_path / "codecompanion-workspace.json"
    assert json_path.exists()

    # Now we can uncomment and fix the test
    with open(json_path) as f:
        data = json.load(f)

    # Should have discovered our test files
    all_files = {f["path"] for group in data["groups"] for f in group["files"]}
    print(f"\nDiscovered files: {all_files}")  # Print discovered files
    assert "src/main.py" in all_files
    assert "tests/test_main.py" in all_files
    assert "README.md" in all_files


def test_ignore_dot_directories(tmp_path: Path) -> None:
    """Test that dot directories are properly ignored"""
    # Create test structure with dot directories
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git/config").write_text("git config")
    (tmp_path / ".mypy_cache").mkdir()
    (tmp_path / ".mypy_cache/cache.json").write_text("cache")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("print('hello')")
    (tmp_path / "src/.local").mkdir()
    (tmp_path / "src/.local/state.json").write_text("state")

    # Create group with pattern to match all files
    group = Group(
        name="Test",
        description="Test group",
        files=[
            File(path="**/*", description="All files", kind="pattern"),
        ],
    )

    # Test pattern resolution
    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Verify no dot directories are included
    assert "src/main.py" in paths
    assert ".git/config" not in paths
    assert ".mypy_cache/cache.json" not in paths
    assert ".pytest_cache" not in paths
    assert "src/.local/state.json" not in paths
    print(f"Resolved paths: {paths}")  # For debugging


def test_ignore_empty_files(tmp_path: Path) -> None:
    """Test that empty files are properly ignored"""
    # Create test files
    (tmp_path / "empty.txt").write_text("")
    (tmp_path / "nonempty.txt").write_text("content")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/empty.py").write_text("")
    (tmp_path / "src/code.py").write_text("print('hello')")

    group = Group(
        name="Test",
        description="Test group",
        files=[
            File(path="**/*", description="All files", kind="pattern"),
        ],
    )

    # Test pattern resolution
    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Verify empty files are excluded
    assert "nonempty.txt" in paths
    assert "src/code.py" in paths
    assert "empty.txt" not in paths
    assert "src/empty.py" not in paths
    print(f"Resolved paths: {paths}")  # For debugging


def test_combined_ignore_patterns(tmp_path: Path) -> None:
    """Test combination of ignore patterns
    (dot dirs, empty files, and other patterns)"""
    # Create complex test structure
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git/config").write_text("git config")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("print('hello')")
    (tmp_path / "src/empty.py").write_text("")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules/package.json").write_text("{}")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__/main.cpython-39.pyc").write_text("bytecode")
    (tmp_path / "temp.log").write_text("log")

    group = Group(
        name="Test",
        description="Test group",
        files=[
            File(path="**/*", description="All files", kind="pattern"),
        ],
    )

    # Test pattern resolution
    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Verify all ignore patterns work together
    assert "src/main.py" in paths  # Should include
    assert ".git/config" not in paths  # Dot directory
    assert "src/empty.py" not in paths  # Empty file
    assert "node_modules/package.json" not in paths  # Ignored directory
    assert "__pycache__/main.cpython-39.pyc" not in paths  # Ignored pattern
    assert "temp.log" not in paths  # Ignored extension
    print(f"Resolved paths: {paths}")  # For debugging


def test_ignore_patterns_with_explicit_files(tmp_path: Path) -> None:
    """Test ignore patterns when mixing patterns and explicit files"""
    # Create test structure
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git/important.txt").write_text("important")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("print('hello')")
    (tmp_path / "src/.env").write_text("SECRET=123")

    group = Group(
        name="Test",
        description="Test group",
        files=[
            # Pattern-based discovery - follows ignore rules
            File(path="**/*.py", description="Python files", kind="pattern"),
            # Explicit files - bypass ignore rules
            File(path=".git/important.txt", description="Important file", kind="file"),
            File(path="src/.env", description="Env file", kind="file"),
        ],
    )

    # Test pattern resolution
    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Verify behavior
    assert "src/main.py" in paths  # Include from pattern
    assert ".git/important.txt" in paths  # Include explicit file even in dot dir
    assert "src/.env" in paths  # Include explicit file even if hidden


def test_ignore_nested_dot_directories(tmp_path: Path) -> None:
    """Test ignoring of deeply nested dot directories and their contents"""
    # Create nested structure with dot directories at different levels
    (tmp_path / "src/valid/nested/.config").mkdir(parents=True)
    (tmp_path / "src/valid/.local/share").mkdir(parents=True)
    (tmp_path / "src/.vscode/settings").mkdir(parents=True)

    # Add some files
    (tmp_path / "src/valid/nested/.config/settings.json").write_text("config")
    (tmp_path / "src/valid/.local/share/data.db").write_text("data")
    (tmp_path / "src/.vscode/settings/config.json").write_text("vscode")
    (tmp_path / "src/valid/code.py").write_text("print('hello')")

    group = Group(
        name="Test",
        description="Test group",
        files=[
            File(path="**/*", description="All files", kind="pattern"),
        ],
    )

    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Only non-dot directory files should be included
    assert "src/valid/code.py" in paths
    assert "src/valid/nested/.config/settings.json" not in paths
    assert "src/valid/.local/share/data.db" not in paths
    assert "src/.vscode/settings/config.json" not in paths


def test_zero_byte_files(tmp_path: Path) -> None:
    """Test handling of zero-byte files vs files with only whitespace"""
    # Create various empty-like files
    (tmp_path / "completely_empty.txt").write_text("")
    (tmp_path / "only_newline.txt").write_text("\n")
    (tmp_path / "only_spaces.txt").write_text("   ")
    (tmp_path / "only_tabs.txt").write_text("\t\t")
    (tmp_path / "whitespace_mix.txt").write_text("\n  \t  \n")
    (tmp_path / "actual_content.txt").write_text("hello")

    group = Group(
        name="Test",
        description="Test group",
        files=[
            File(path="*.txt", description="Text files", kind="pattern"),
        ],
    )

    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Only files with actual content should be included
    assert "completely_empty.txt" not in paths
    assert "only_newline.txt" in paths  # Has 1 byte
    assert "only_spaces.txt" in paths  # Has content
    assert "only_tabs.txt" in paths  # Has content
    assert "whitespace_mix.txt" in paths  # Has content
    assert "actual_content.txt" in paths


def test_symlink_handling(tmp_path: Path) -> None:
    """Test handling of symlinks to files and directories"""
    # Create real files and directories
    (tmp_path / "real_dir").mkdir()
    (tmp_path / "real_dir/file.txt").write_text("content")
    (tmp_path / ".hidden_dir").mkdir()
    (tmp_path / ".hidden_dir/file.txt").write_text("hidden")

    # Create symlinks
    (tmp_path / "link_to_file").symlink_to(tmp_path / "real_dir/file.txt")
    (tmp_path / "link_to_dir").symlink_to(tmp_path / "real_dir")
    (tmp_path / "link_to_hidden").symlink_to(tmp_path / ".hidden_dir")

    group = Group(
        name="Test",
        description="Test group",
        files=[
            File(path="**/*", description="All files", kind="pattern"),
        ],
    )

    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Check symlink handling
    assert "real_dir/file.txt" in paths
    assert "link_to_file" in paths  # Symlink to regular file should be included
    assert ".hidden_dir/file.txt" not in paths
    assert (
        "link_to_hidden/file.txt" not in paths
    )  # Symlink to hidden dir should be excluded


def test_file_size_edge_cases(tmp_path: Path) -> None:
    """Test handling of files with various sizes including edge cases"""
    # Create files with different sizes
    (tmp_path / "empty.txt").write_text("")  # 0 bytes
    (tmp_path / "one_byte.txt").write_text("a")  # 1 byte
    (tmp_path / "one_char_unicode.txt").write_text("🌟")  # Multi-byte unicode
    (tmp_path / "binary.dat").write_bytes(bytes([0]))  # 1 byte binary

    group = Group(
        name="Test",
        description="Test group",
        files=[
            File(path="*.*", description="All files", kind="pattern"),
        ],
    )

    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Verify size handling
    assert "empty.txt" not in paths  # Should be ignored
    assert "one_byte.txt" in paths  # Should be included
    assert "one_char_unicode.txt" in paths  # Should be included
    assert "binary.dat" in paths  # Should be included


def test_pattern_combinations(tmp_path: Path) -> None:
    """Test various glob pattern combinations with ignore rules"""
    # Create test structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("content")
    (tmp_path / "src/.env").write_text("secret")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_main.py").write_text("test")
    (tmp_path / "tests/.pytest_cache").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/index.md").write_text("docs")
    (tmp_path / "docs/.vitepress").mkdir()

    group = Group(
        name="Test",
        description="Test group",
        files=[
            File(path="**/*.py", description="Python files", kind="pattern"),
            File(path="docs/**/*", description="Doc files", kind="pattern"),
            File(path="**/.*", description="Dot files", kind="pattern"),
        ],
    )

    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Verify pattern handling
    assert "src/main.py" in paths
    assert "tests/test_main.py" in paths
    assert "docs/index.md" in paths
    assert "src/.env" not in paths
    assert "tests/.pytest_cache" not in paths
    assert "docs/.vitepress" not in paths


def test_ignore_lock_files(tmp_path: Path) -> None:
    """Test that package lock files are properly ignored"""
    # Create test structure with various lock files
    lock_files = [
        "uv.lock",
        "poetry.lock",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Cargo.lock",
        "Gemfile.lock",
        "composer.lock",
        "mix.lock",
        "go.sum",
    ]

    # Create lock files and a regular file
    for lock_file in lock_files:
        (tmp_path / lock_file).write_text("lock content")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("print('hello')")

    group = Group(
        name="Test",
        description="Test group",
        files=[
            File(path="**/*", description="All files", kind="pattern"),
        ],
    )

    # Test pattern resolution
    resolved = group.resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Verify no lock files are included
    assert "src/main.py" in paths  # Regular file should be included
    for lock_file in lock_files:
        assert lock_file not in paths, f"{lock_file} should be ignored"

    print(f"Resolved paths: {paths}")  # For debugging


def test_custom_ignore_patterns(tmp_path: Path) -> None:
    """Test customization of ignore patterns"""
    # Create test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("print('hello')")
    (tmp_path / "custom.lock").write_text("lock")
    (tmp_path / ".env").write_text("SECRET=123")
    (tmp_path / "uv.lock").write_text("lock")

    # Create workspace with custom ignore config
    workspace = Workspace(
        name="test",
        description="Test workspace",
        ignore=WorkspaceIgnore(
            enabled=True,
            patterns={
                "default": [
                    "custom.lock",
                    "special.lock",
                    ".env",
                ],  # Override default patterns
            },
            additional=["extra.ignore"],  # Add custom pattern
            categories=["default"],  # Use only default category
        ),
        groups=[
            Group(
                name="Test",
                description="Test group",
                files=[
                    File(path="**/*", description="All files", kind="pattern"),
                ],
            )
        ],
    )

    # Resolve patterns
    ignore_patterns = workspace.get_ignore_patterns()

    # Update patterns for files
    for group in workspace.groups:
        for file in group.files:
            file.ignore_patterns = ignore_patterns

    # Test pattern resolution
    resolved = workspace.groups[0].resolve_patterns(tmp_path)
    paths = {f["path"] for f in resolved["files"]}

    # Verify custom ignore patterns
    assert "src/main.py" in paths  # Should include
    assert "custom.lock" not in paths  # Should ignore (custom pattern)
    assert ".env" not in paths  # Should ignore (custom pattern)
    assert "uv.lock" in paths  # Should include (not in patterns)
