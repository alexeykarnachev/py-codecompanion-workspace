import fnmatch
import importlib.resources
import json
import re
import subprocess
from pathlib import Path
from typing import Any, ClassVar, Literal

import typer
import yaml
from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress, TextColumn
from rich.prompt import Confirm

app = typer.Typer()
console = Console()

# CLI Arguments
INIT_PATH_ARG = typer.Argument(
    default=".",
    help="Project path or name. Use '.' for current directory",
)

INIT_FORCE_OPT = typer.Option(
    False,
    "--force",
    "-f",
    help="Force overwrite existing files",
)

INIT_TEMPLATE_OPT = typer.Option(
    None,
    help="Template to use",
)

COMPILE_CONFIG_ARG = typer.Argument(
    ...,
    help="Path to YAML config",
    exists=True,
    dir_okay=False,
    file_okay=True,
)

COMPILE_OUTPUT_OPT = typer.Option(
    None,
    help="Output JSON path",
    dir_okay=False,
    file_okay=True,
)


class File(BaseModel):
    description: str | None = None
    path: str
    kind: Literal["file", "pattern"] = "file"
    _ignore_patterns: set[str] | None = None

    model_config = {
        "arbitrary_types_allowed": True,
    }

    DEFAULT_IGNORE_PATTERNS: ClassVar[dict[str, set[str]]] = {
        "default": {
            # Dependencies
            "node_modules/",
            "venv/",
            ".env/",
            "__pycache__/",
            "*.pyc",
            "target/",
            "dist/",
            "build/",
            ".tox/",
            ".pytest_cache/",
            ".coverage",
            "coverage/",
            ".hypothesis/",
            # IDE
            "*.swp",
            ".DS_Store",
            ".idea/",
            ".vscode/",
            "*.sublime-*",
            ".project",
            ".settings/",
            ".classpath",
            "*.iml",
            # Temp
            "*.log",
            "tmp/",
            "temp/",
            "*.tmp",
            "*.bak",
            "*~",
            # Packages
            "*.egg-info/",
            "*.egg",
            "*.whl",
            "*.tar.gz",
            "*.zip",
            # Workspace
            ".cc/",
            ".git/",
            ".hg/",
            ".svn/",
            # Locks
            "*.lock",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "go.sum",
        },
    }

    @property
    def ignore_patterns(self) -> set[str]:
        """Get ignore patterns, using defaults if not set"""
        if self._ignore_patterns is None:
            return {
                pattern
                for patterns in self.DEFAULT_IGNORE_PATTERNS.values()
                for pattern in patterns
            }
        return self._ignore_patterns

    @ignore_patterns.setter
    def ignore_patterns(self, patterns: set[str]) -> None:
        self._ignore_patterns = patterns

    def should_ignore(self, path: str) -> bool:
        """Check if path matches any ignore pattern"""
        # Don't apply ignore patterns to explicitly listed files
        if self.kind == "file":
            return False

        # Normalize path
        path = str(path)
        if path.startswith("./"):
            path = path[2:]

        # Check for dot directories in path parts
        path_parts = Path(path).parts
        if any(part.startswith(".") for part in path_parts):
            return True

        # For patterns, check other ignore rules
        return any(
            fnmatch.fnmatch(path, pattern) if "*" in pattern else pattern in path
            for pattern in self.ignore_patterns
        )

    def resolve(self, base_path: Path) -> list["File"]:
        """Resolve pattern into actual files"""
        if self.kind == "pattern":
            resolved = []
            try:
                # Handle different glob patterns
                if "**" in self.path:
                    paths = base_path.rglob(self.path.replace("**/", ""))
                else:
                    paths = base_path.glob(self.path)

                # Process found paths
                for path in sorted(paths):
                    if not path.is_file():
                        continue

                    rel_path = str(path.relative_to(base_path))

                    # Skip empty files
                    if path.stat().st_size == 0:
                        continue

                    # Skip ignored paths
                    if self.should_ignore(rel_path):
                        continue

                    resolved.append(
                        File(
                            path=rel_path,
                            description=self.description,
                            kind="file",
                        )
                    )
            except Exception as e:
                print(f"Error resolving pattern {self.path}: {e}")
                return []

            return resolved
        else:
            # For explicit files, check if they should be ignored
            path = base_path / self.path
            if path.is_file() and path.stat().st_size > 0:
                rel_path = str(path.relative_to(base_path))
                if self.should_ignore(rel_path):
                    return []
                return [self]
            return []


class Group(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str = ""
    files: list[File] = Field(default_factory=list)
    symbols: list[File] = Field(default_factory=list)

    def resolve_patterns(self, base_path: Path) -> dict[str, Any]:
        """Resolve file patterns into actual files"""
        data = self.model_dump()

        # Resolve patterns to actual files
        resolved_files = []
        for file in self.files:
            resolved_files.extend(file.resolve(base_path))
        data["files"] = [
            {"path": f.path, "description": f.description} for f in resolved_files
        ]

        return data


class WorkspaceIgnore(BaseModel):
    enabled: bool = True
    patterns: dict[str, list[str]] = Field(default_factory=dict)
    additional: list[str] = Field(default_factory=list)
    categories: list[str] = Field(
        default_factory=lambda: list(File.DEFAULT_IGNORE_PATTERNS.keys())
    )


class Workspace(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str = ""
    groups: list[Group] = Field(default_factory=list)
    ignore: WorkspaceIgnore = Field(default_factory=WorkspaceIgnore)

    def get_ignore_patterns(self) -> set[str]:
        """Get combined ignore patterns based on config"""
        if not self.ignore.enabled:
            return set()

        patterns = set()

        # Add patterns from enabled categories
        for category in self.ignore.categories:
            if category in File.DEFAULT_IGNORE_PATTERNS:
                patterns.update(File.DEFAULT_IGNORE_PATTERNS[category])

        # Override with custom patterns
        for category, custom_patterns in self.ignore.patterns.items():
            if category in File.DEFAULT_IGNORE_PATTERNS:
                # Remove default patterns for this category
                patterns.difference_update(File.DEFAULT_IGNORE_PATTERNS[category])
                # Add custom patterns
                patterns.update(custom_patterns)

        # Add additional patterns
        patterns.update(self.ignore.additional)

        return patterns

    def resolve_patterns(self, base_path: Path) -> dict[str, Any]:
        """Resolve patterns in all groups"""
        data = {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "groups": [g.resolve_patterns(base_path) for g in self.groups],
        }
        return data


class Template(BaseModel):
    name: str
    description: str
    content: str
    variables: dict[str, str] = Field(
        default_factory=lambda: {"project_name": "Project name"}
    )

    def render(self, **kwargs: Any) -> Workspace:
        """Render template with variables and return validated Workspace"""
        content = self.content.format(**kwargs)
        config = yaml.safe_load(content)
        return Workspace(**config)


class TemplateLibrary(BaseModel):
    templates: dict[str, Template] = Field(default_factory=dict)

    def get(self, name: str) -> Template | None:
        return self.templates.get(name)

    def list_templates(self) -> list[str]:
        return list(self.templates.keys())


class FileContent(BaseModel):
    description: str | None = None
    path: str
    content: str


class DataFiles:
    CONVENTIONS = FileContent(
        path="CONVENTIONS.md",
        description="Project conventions and guidelines",
        content=importlib.resources.files("cc_workspace.data")
        .joinpath("CONVENTIONS.md")
        .read_text(),
    )
    CODECOMPANION_DOC = FileContent(
        path="codecompanion_doc.md",
        description="CodeCompanion documentation",
        content=importlib.resources.files("cc_workspace.data")
        .joinpath("codecompanion_doc.md")
        .read_text(),
    )


def ensure_cc_structure(path: Path) -> tuple[Path, Path]:
    """Create .cc directory structure"""
    cc_dir = path / ".cc"
    data_dir = cc_dir / "data"

    cc_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # Create default files
    for file in [DataFiles.CONVENTIONS, DataFiles.CODECOMPANION_DOC]:
        file_path = data_dir / file.path
        if not file_path.exists():
            with open(file_path, "w") as f:
                f.write(file.content)

    return cc_dir, data_dir


def load_templates() -> TemplateLibrary:
    """Load all templates from data/templates directory"""
    templates = {}
    template_dir = importlib.resources.files("cc_workspace.data.templates")

    for template_path in template_dir.iterdir():
        if Path(str(template_path)).suffix == ".yaml":
            name = Path(str(template_path)).stem
            content = template_path.read_text()
            templates[name] = Template(
                name=name,
                description=f"{name.title()} template",
                content=content,
            )

    return TemplateLibrary(templates=templates)


TEMPLATES = load_templates()


def ensure_cc_dir(path: Path) -> Path:
    """Ensure .cc directory exists and return its path"""
    cc_dir = path / ".cc"
    cc_dir.mkdir(exist_ok=True)
    return cc_dir


def create_workspace(path: Path, template_name: str | None = None) -> tuple[Path, Path]:
    """Create a new workspace and return paths to yaml config and cc dir"""
    cc_dir, _ = ensure_cc_structure(path)
    config_path = cc_dir / "codecompanion.yaml"
    project_name = path.absolute().name

    # Get and validate template
    template = TEMPLATES.get(template_name or "default")
    if not template:
        available = TEMPLATES.list_templates()
        raise ValueError(
            f"Template '{template_name}' not found. Available: {available}"
        )

    # Render template and validate
    workspace = template.render(project_name=project_name)

    # Write to file
    with open(config_path, "w") as f:
        yaml.dump(workspace.resolve_patterns(base_path=path), f, sort_keys=False)

    return config_path, cc_dir


def validate_workspace_files(workspace: Workspace, base_path: Path) -> list[str]:
    """Validate all files in workspace exist"""
    errors = []

    for group in workspace.groups:
        for file in group.files:
            # Skip validation for glob patterns
            if any(char in file.path for char in "*?[]"):
                continue

            path = base_path / file.path
            if not path.exists():
                errors.append(f"File not found: {file.path}")

        for symbol in group.symbols:
            path = base_path / symbol.path
            if not path.exists():
                errors.append(f"Symbol file not found: {symbol.path}")

    return errors


def compile_workspace(
    config_path: Path,
    output_path: Path | None = None,
) -> None:
    """Compile YAML to JSON"""
    if not output_path:
        output_path = config_path.parent.parent / "codecompanion-workspace.json"

    base_path = config_path.parent.parent

    # Read and validate YAML
    with open(config_path) as f:
        config = yaml.safe_load(f)

    workspace = Workspace(**config)

    # Validate files exist
    errors = validate_workspace_files(workspace, config_path.parent.parent)
    if errors:
        raise ValueError("\n".join(["Invalid workspace:", *errors]))

    # Write JSON with resolved patterns
    with open(output_path, "w") as f:
        data = workspace.resolve_patterns(base_path=base_path)
        f.write(json.dumps(data, indent=2))


def to_package_name(name: str) -> str:
    """Convert project name to valid Python package name"""
    return re.sub(r"[-.]", "_", name.lower())


class ProjectInitializer:
    """Handles new project initialization"""

    INIT_CONTENT: ClassVar[str] = '__version__ = "0.1.0"\n'

    MAIN_CONTENT: ClassVar[
        str
    ] = """def main() -> None:
    print("Hello, World!")

if __name__ == "__main__":
    main()
"""

    TEST_CONTENT: ClassVar[
        str
    ] = """def test_version() -> None:
    import {package_name}
    assert {package_name}.__version__ == "0.1.0"
"""

    CHECK_SCRIPT_CONTENT: ClassVar[
        str
    ] = """#!/bin/bash
set -e

echo "🔍 Running complete verification..."

echo "├─ Running ruff..."
ruff check \\
    {package_name}/ \\
    tests/ \\
    scripts/ \\
    --select F,E,W,I,N,UP,B,A,C4,SIM,ERA,PL,RUF \\
    --fix

echo "├─ Running mypy..."
mypy --strict --ignore-missing-imports {package_name}/ tests/ scripts/

echo "└─ Running tests..."
pytest -v tests/

echo "✨ All checks passed!"
"""

    PYPROJECT_CONTENT: ClassVar[
        str
    ] = """[project]
name = "{package_name}"
dynamic = ["version"]
description = "Project description"
readme = "README.md"
requires-python = ">=3.13"
license = "MIT"
authors = [
    {{ name = "Your Name", email = "your.email@example.com" }}
]
dependencies = []

[project.urls]
homepage = "https://github.com/{git_username}/{package_name}"
repository = "https://github.com/{git_username}/{package_name}"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.version]
path = "{package_name}/__init__.py"

[tool.hatch.build]
include = [
    "{package_name}/**/*.py",
    "{package_name}/**/*.md",
]

[tool.hatch.build.targets.wheel]
packages = ["{package_name}"]

[project.scripts]
{package_name} = "{package_name}.main:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
markers = [
    "asyncio: mark test as async/await test",
]

[tool.ruff]
target-version = "py313"
line-length = 88
indent-width = 4
extend-exclude = [".pytest_cache", ".ruff_cache", ".venv", "venv"]

[tool.ruff.lint]
select = [
    "F",     # Pyflakes
    "E",     # pycodestyle errors
    "W",     # pycodestyle warnings
    "I",     # isort
    "N",     # pep8-naming
    "UP",    # pyupgrade
    "B",     # flake8-bugbear
    "A",     # flake8-builtins
    "C4",    # flake8-comprehensions
    "SIM",   # flake8-simplify
    "ERA",   # eradicate
    "PL",    # pylint
    "RUF",   # ruff-specific rules
    "F841",  # unused variables
]
per-file-ignores = {{ "__init__.py" = ["F401"], "tests/*" = ["PLR2004"] }}

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.mypy]
python_version = "3.13"
strict = true
ignore_missing_imports = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true
warn_unreachable = true
"""
    README_CONTENT: ClassVar[
        str
    ] = """# {package_name}

A Python project created with CodeCompanion ✨

## Quick Start

```bash
# Install package
uv add git+https://github.com/username/{package_name}

# Or install in development mode
uv add --dev .
```

## License

MIT
"""

    CHANGELOG_CONTENT: ClassVar[
        str
    ] = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Initial project structure
"""

    GITIGNORE_CONTENT: ClassVar[
        str
    ] = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.tox/
.coverage
.coverage.*
.cache
coverage.xml
*.cover
.pytest_cache/
.mypy_cache/

# Project specific
.cc/
codecompanion-workspace.json
"""

    def __init__(self, path: Path, project_name: str | None = None) -> None:
        self.base_path = path
        self.project_name = project_name or path.name
        self.package_name = to_package_name(self.project_name)

    def _get_git_username(self) -> str:
        """Get Git username from config or return 'username'"""
        try:
            # First check if git is available
            subprocess.run(
                ["git", "--version"],
                check=True,
                capture_output=True,
            )

            # Then try to get username
            result = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                check=True,
            )
            username = result.stdout.strip()
            # Convert to lowercase and remove spaces/special chars for URL
            return re.sub(r"[^a-zA-Z0-9]", "", username.lower())
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "username"

    def _init_git(self) -> None:
        """Initialize git repository"""
        try:
            # First check if git is available
            subprocess.run(
                ["git", "--version"],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print(
                "[yellow]Warning: Git not available, "
                "skipping repository initialization[/yellow]"
            )
            return

        try:
            subprocess.run(
                ["git", "init", "--quiet"],
                cwd=self.base_path,
                check=True,
            )
            # Add initial commit with all scaffolded files
            subprocess.run(
                ["git", "add", "."],
                cwd=self.base_path,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "Initial commit ✨"],
                cwd=self.base_path,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            console.print(
                f"[yellow]Warning: Failed to initialize git repository: {e}[/yellow]"
            )

    def _install_dev_tools(self) -> None:
        """Install development tools using uv"""
        try:
            subprocess.run(
                [
                    "uv",
                    "add",
                    "--dev",
                    "mypy>=1.9.0",
                    "pytest>=8.1.1",
                    "pytest-asyncio>=0.23.5.post1",
                    "pytest-cov>=4.1.0",
                    "ruff>=0.3.3",
                    "types-pyyaml>=6.0.12.20240311",
                ],
                check=True,
                cwd=self.base_path,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            console.print(
                f"[yellow]Warning: Failed to install dev dependencies: {e}[/yellow]"
            )

    def create_structure(self) -> None:
        """Create project directory structure"""
        # Create base dir if doesn't exist
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True)

        # Get Git username for pyproject.toml
        git_username = self._get_git_username()

        # Project dirs
        pkg_dir = self.base_path / self.package_name
        test_dir = self.base_path / "tests"
        script_dir = self.base_path / "scripts"

        for d in [pkg_dir, test_dir, script_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Documentation files
        (self.base_path / "README.md").write_text(
            self.README_CONTENT.format(package_name=self.package_name)
        )
        (self.base_path / "CHANGELOG.md").write_text(self.CHANGELOG_CONTENT)
        (self.base_path / ".gitignore").write_text(self.GITIGNORE_CONTENT)

        # Basic files
        (pkg_dir / "__init__.py").write_text(self.INIT_CONTENT)
        (pkg_dir / "main.py").write_text(self.MAIN_CONTENT)
        (test_dir / "__init__.py").touch()
        (test_dir / "test_basic.py").write_text(
            self.TEST_CONTENT.format(package_name=self.package_name)
        )

        # Create check script
        check_script = script_dir / "ccw_check.sh"
        check_script.write_text(
            self.CHECK_SCRIPT_CONTENT.format(package_name=self.package_name)
        )
        check_script.chmod(0o755)  # Make executable

        # Create pyproject.toml with Git username
        pyproject = self.base_path / "pyproject.toml"
        pyproject.write_text(
            self.PYPROJECT_CONTENT.format(
                package_name=self.package_name,
                git_username=git_username,
            )
        )

        # Install dev tools first, before Git initialization
        try:
            self._install_dev_tools()
        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to install dev dependencies: {e}[/yellow]"
            )
            return

        # Initialize git last, after all files are created and deps installed
        try:
            self._init_git()
        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to initialize git repository: {e}[/yellow]"
            )


@app.command()
def init(
    path: Path = INIT_PATH_ARG,
    force: bool = INIT_FORCE_OPT,
    template: str | None = INIT_TEMPLATE_OPT,
) -> None:
    """Initialize a new Python project with CodeCompanion workspace"""
    try:
        # Combine nested if statements
        if template is not None and template not in TEMPLATES.list_templates():
            console.print(f"[red]Error: Template '{template}' not found[/red]")
            raise typer.Exit(1)

        # Handle project path
        if str(path) == ".":
            # Just initialize workspace files in current directory
            project_path = Path.cwd()
            project_name = None
            create_project = False
        else:
            # Create new project in the specified directory
            project_path = Path.cwd() / path
            project_name = path.name
            create_project = True

            # Combine nested if statements
            if (
                project_path.exists()
                and not force
                and not Confirm.ask(
                    f"\nDirectory {project_path} already exists. Initialize anyway?",
                    default=False,
                )
            ):
                raise typer.Exit(0)

        # Create project structure and workspace
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            try:
                if create_project:
                    progress.add_task("├─ Creating project structure...", total=None)
                    initializer = ProjectInitializer(project_path, project_name)
                    initializer.create_structure()

                # Initialize workspace
                progress.add_task("├─ Initializing workspace...", total=None)
                config_path, cc_dir = create_workspace(project_path, template)

                progress.add_task("└─ Compiling workspace config...", total=None)
                compile_workspace(config_path)

                if create_project:
                    console.print(f"\n✨ Created new project at {project_path}")
                    console.print(f"📁 Project files in {project_path}")
                else:
                    console.print("\n✨ Initialized workspace in current directory")
                console.print(f"📁 CCW files in {cc_dir}")

                return  # Success case

            except Exception as e:
                console.print(f"[red]Error during initialization: {e}[/red]")
                raise typer.Exit(1) from e

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def compile_config(
    config: Path = COMPILE_CONFIG_ARG,
    output: Path | None = COMPILE_OUTPUT_OPT,
) -> None:
    """Compile YAML config to CodeCompanion workspace JSON"""
    try:
        compile_workspace(config, output)
        console.print("✨ Compiled workspace config")
    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
