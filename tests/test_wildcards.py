import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from loguru import logger
from typer.testing import CliRunner

from cc_workspace.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def complex_project(tmp_path: Path) -> Path:
    """Create a complex project structure for testing wildcards"""
    # Source code structure
    (tmp_path / "src/pkg/subpkg").mkdir(parents=True)
    (tmp_path / "src/pkg/__init__.py").write_text("# Init")
    (tmp_path / "src/pkg/main.py").write_text("# Main")
    (tmp_path / "src/pkg/subpkg/__init__.py").write_text("# Sub init")
    (tmp_path / "src/pkg/subpkg/module.py").write_text("# Module")

    # Test structure
    (tmp_path / "tests/unit/deep").mkdir(parents=True)
    (tmp_path / "tests/integration").mkdir()
    (tmp_path / "tests/test_main.py").write_text("# Test main")
    (tmp_path / "tests/unit/test_unit.py").write_text("# Test unit")
    (tmp_path / "tests/unit/deep/test_deep.py").write_text("# Test deep")
    (tmp_path / "tests/integration/test_integration.py").write_text(
        "# Test integration"
    )

    # Documentation structure
    (tmp_path / "docs/api/reference").mkdir(parents=True)
    (tmp_path / "docs/index.md").write_text("# Index")
    (tmp_path / "docs/api/overview.md").write_text("# API Overview")
    (tmp_path / "docs/api/reference/details.md").write_text("# API Details")

    # Mixed content directories
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/tool.py").write_text("# Tool")
    (tmp_path / "scripts/docs.md").write_text("# Script docs")

    # Print directory structure for debugging
    print("\nProject structure:")
    for path in sorted(tmp_path.rglob("*")):
        if path.is_file():
            print(f"  {path.relative_to(tmp_path)}")

    return tmp_path


def create_test_config(case: dict[str, Any]) -> str:
    """Create YAML config content for test case"""
    if "patterns" in case:
        # Multiple patterns
        files = [
            {"path": pattern, "kind": "pattern", "description": "Test pattern"}
            for pattern in case["patterns"]
        ]
    else:
        # Single pattern
        files = [
            {"path": case["pattern"], "kind": "pattern", "description": "Test pattern"}
        ]

    config = {"name": "test-project", "groups": [{"name": "Test", "files": files}]}

    return yaml.dump(config, sort_keys=False)


def test_wildcard_patterns(complex_project: Path, runner: CliRunner) -> None:
    """Test various wildcard pattern combinations"""
    # Enable detailed logging for pattern resolution
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        level="TRACE",
        format="<level>{time:HH:mm:ss}|{level}| {message}</level>",
    )

    test_cases = [
        {
            "name": "Simple star pattern",
            "pattern": "src/pkg/*.py",
            "expected": {"src/pkg/main.py", "src/pkg/__init__.py"},
        },
        {
            "name": "Deep recursive pattern",
            "pattern": "src/**/*.py",
            "expected": {
                "src/pkg/main.py",
                "src/pkg/__init__.py",
                "src/pkg/subpkg/__init__.py",
                "src/pkg/subpkg/module.py",
            },
        },
        {
            "name": "Multiple extensions",
            "pattern": "scripts/*.*",
            "expected": {"scripts/tool.py", "scripts/docs.md"},
        },
        {
            "name": "Nested test pattern",
            "pattern": "tests/**/*test_*.py",
            "expected": {
                "tests/test_main.py",
                "tests/unit/test_unit.py",
                "tests/unit/deep/test_deep.py",
                "tests/integration/test_integration.py",
            },
        },
        {
            "name": "Specific depth pattern",
            "pattern": "docs/*/*.md",
            "expected": {"docs/api/overview.md"},
        },
        {
            "name": "Complex nested docs",
            "pattern": "docs/**/*.md",
            "expected": {
                "docs/index.md",
                "docs/api/overview.md",
                "docs/api/reference/details.md",
            },
        },
        {
            "name": "Multiple patterns combined",
            "patterns": ["**/*.py", "**/*.md"],
            "expected": {
                # Python files
                "src/pkg/main.py",
                "src/pkg/__init__.py",
                "src/pkg/subpkg/__init__.py",
                "src/pkg/subpkg/module.py",
                "scripts/tool.py",
                "tests/test_main.py",
                "tests/unit/test_unit.py",
                "tests/unit/deep/test_deep.py",
                "tests/integration/test_integration.py",
                # Markdown files
                "docs/index.md",
                "docs/api/overview.md",
                "docs/api/reference/details.md",
                "scripts/docs.md",
            },
        },
    ]

    for case in test_cases:
        logger.info(f"\nTesting: {case['name']}")

        # Create config with the test pattern(s)
        yaml_content = create_test_config(case)

        # Write config and compile
        cc_dir = complex_project / ".cc"
        cc_dir.mkdir(exist_ok=True)
        config_path = cc_dir / "codecompanion.yaml"
        config_path.write_text(yaml_content)

        # Run compilation
        result = runner.invoke(app, ["compile-config", str(config_path)])
        assert result.exit_code == 0, f"Config compilation failed for {case['name']}"

        # Load and verify results
        with open(complex_project / "codecompanion-workspace.json") as f:
            data = json.loads(f.read())
            found_files = {f["path"] for g in data["groups"] for f in g["files"]}

            # Debug output
            logger.debug(f"Expected files: {sorted(case['expected'])}")
            logger.debug(f"Found files: {sorted(found_files)}")

            # Detailed diff logging
            missing = set(case["expected"]) - found_files
            extra = found_files - set(case["expected"])
            if missing:
                logger.warning(f"Missing files: {missing}")
            if extra:
                logger.warning(f"Extra files: {extra}")

            assert found_files == case["expected"], (
                f"Pattern mismatch for {case['name']}\n"
                f"Expected: {sorted(case['expected'])}\n"
                f"Found: {sorted(found_files)}"
            )


def test_edge_case_patterns(complex_project: Path, runner: CliRunner) -> None:
    """Test edge cases and potential problem patterns"""
    test_cases = [
        {
            "name": "Double asterisk at start",
            "pattern": "**/*.py",
            "expected": {
                "src/pkg/main.py",
                "src/pkg/__init__.py",
                "src/pkg/subpkg/__init__.py",
                "src/pkg/subpkg/module.py",
                "scripts/tool.py",
                "tests/test_main.py",
                "tests/unit/test_unit.py",
                "tests/unit/deep/test_deep.py",
                "tests/integration/test_integration.py",
            },
        },
        {
            "name": "Double asterisk in middle",
            "pattern": "tests/**/test_*.py",
            "expected": {
                "tests/test_main.py",
                "tests/unit/test_unit.py",
                "tests/unit/deep/test_deep.py",
                "tests/integration/test_integration.py",
            },
        },
        {
            "name": "Multiple consecutive stars",
            "pattern": "src/**/**/*.py",
            "expected": {
                "src/pkg/main.py",
                "src/pkg/__init__.py",
                "src/pkg/subpkg/__init__.py",
                "src/pkg/subpkg/module.py",
            },
        },
        {
            "name": "Empty directory traversal",
            "pattern": "src//pkg//*.py",  # Double slashes
            "expected": {
                "src/pkg/main.py",
                "src/pkg/__init__.py",
            },
        },
        {
            "name": "Single file match",
            "pattern": "**/main.py",
            "expected": {"src/pkg/main.py"},
        },
    ]

    for case in test_cases:
        logger.info(f"\nTesting edge case: {case['name']}")
        yaml_content = create_test_config(case)

        cc_dir = complex_project / ".cc"
        cc_dir.mkdir(exist_ok=True)
        config_path = cc_dir / "codecompanion.yaml"
        config_path.write_text(yaml_content)

        result = runner.invoke(app, ["compile-config", str(config_path)])
        assert (
            result.exit_code == 0
        ), f"Config compilation failed for edge case: {case['name']}"

        with open(complex_project / "codecompanion-workspace.json") as f:
            data = json.loads(f.read())
            found_files = {f["path"] for g in data["groups"] for f in g["files"]}

            logger.debug(f"Edge case expected files: {sorted(case['expected'])}")
            logger.debug(f"Edge case found files: {sorted(found_files)}")

            missing = set(case["expected"]) - found_files
            extra = found_files - set(case["expected"])
            if missing:
                logger.warning(f"Missing files in edge case: {missing}")
            if extra:
                logger.warning(f"Extra files in edge case: {extra}")

            assert found_files == case["expected"], (
                f"Edge case pattern mismatch for {case['name']}\n"
                f"Expected: {sorted(case['expected'])}\n"
                f"Found: {sorted(found_files)}"
            )


def test_ignore_pattern_interaction(complex_project: Path, runner: CliRunner) -> None:
    """Test interaction between wildcards and ignore patterns"""
    test_cases = [
        {
            "name": "Ignore with wildcards",
            "pattern": "**/*.py",
            "ignore_patterns": ["**/test_*.py"],
            "expected": {
                "src/pkg/main.py",
                "src/pkg/__init__.py",
                "src/pkg/subpkg/__init__.py",
                "src/pkg/subpkg/module.py",
                "scripts/tool.py",
            },
        },
        {
            "name": "Deep ignore pattern",
            "pattern": "**/*.py",
            "ignore_patterns": ["**/subpkg/**"],
            "expected": {
                "src/pkg/main.py",
                "src/pkg/__init__.py",
                "scripts/tool.py",
                "tests/test_main.py",
                "tests/unit/test_unit.py",
                "tests/unit/deep/test_deep.py",
                "tests/integration/test_integration.py",
            },
        },
    ]

    for case in test_cases:
        logger.info(f"\nTesting ignore pattern: {case['name']}")

        config = {
            "name": "test-project",
            "ignore": {
                "enabled": True,
                "patterns": {"custom": case["ignore_patterns"]},
                "categories": ["custom"],
            },
            "groups": [
                {
                    "name": "Test",
                    "files": [
                        {
                            "path": case["pattern"],
                            "kind": "pattern",
                            "description": "Test pattern",
                        }
                    ],
                }
            ],
        }

        yaml_content = yaml.dump(config, sort_keys=False)

        cc_dir = complex_project / ".cc"
        cc_dir.mkdir(exist_ok=True)
        config_path = cc_dir / "codecompanion.yaml"
        config_path.write_text(yaml_content)

        result = runner.invoke(app, ["compile-config", str(config_path)])
        assert (
            result.exit_code == 0
        ), f"Config compilation failed for ignore pattern: {case['name']}"

        with open(complex_project / "codecompanion-workspace.json") as f:
            data = json.loads(f.read())
            found_files = {f["path"] for g in data["groups"] for f in g["files"]}

            logger.debug(f"Ignore pattern expected files: {sorted(case['expected'])}")
            logger.debug(f"Ignore pattern found files: {sorted(found_files)}")

            missing = set(case["expected"]) - found_files
            extra = found_files - set(case["expected"])
            if missing:
                logger.warning(f"Missing files in ignore pattern: {missing}")
            if extra:
                logger.warning(f"Extra files in ignore pattern: {extra}")

            assert found_files == case["expected"], (
                f"Ignore pattern mismatch for {case['name']}\n"
                f"Expected: {sorted(case['expected'])}\n"
                f"Found: {sorted(found_files)}"
            )


def test_init_preserves_patterns(complex_project: Path, runner: CliRunner) -> None:
    """Test that initialization preserves wildcards in yaml config"""
    with runner.isolated_filesystem(temp_dir=complex_project) as fs:
        # Initialize workspace
        result = runner.invoke(app, ["init", "."])
        assert result.exit_code == 0

        # Check that yaml contains patterns, not resolved files
        yaml_path = Path(fs) / ".cc" / "codecompanion.yaml"
        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        # Verify pattern is preserved
        files = config["groups"][0]["files"]
        assert any(
            f["path"] == "**/*" and f["kind"] == "pattern" for f in files
        ), "Wildcard pattern should be preserved in yaml config"

        # Verify only CONVENTIONS.md is listed explicitly
        explicit_files = [f for f in files if f["kind"] == "file"]
        assert len(explicit_files) == 1
        assert explicit_files[0]["path"] == ".cc/data/CONVENTIONS.md"
