from pathlib import Path

import pytest

from cc_workspace.tools.merge_docs import (
    CombinerConfig,
    ProcessingConfig,
    SourceFile,
    discover_files,
    process_file,
)


@pytest.fixture
def test_files(tmp_path: Path) -> Path:
    (tmp_path / "test1.md").write_text("# Header\nContent")
    (tmp_path / "test2.md").write_text("## Header2\nContent2")
    (tmp_path / "ignored.txt").write_text("ignored")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/ignored.md").write_text("ignored")
    return tmp_path


@pytest.mark.asyncio
async def test_discover_files(test_files: Path) -> None:
    config = CombinerConfig(source=test_files, output=test_files / "output.md")
    files = await discover_files(config)
    assert len(files) == 2
    assert all(f.path.suffix == ".md" for f in files)
    assert not any("assets" in str(f.path) for f in files)


@pytest.mark.asyncio
async def test_process_file(test_files: Path) -> None:
    file = SourceFile(path=test_files / "test1.md", level=2)
    config = ProcessingConfig()
    content = await process_file(file, config)
    assert content.startswith("## Header")


@pytest.mark.asyncio
async def test_process_file_with_links(test_files: Path) -> None:
    test_content = "# Title\n[Link](docs/test.md)"
    test_file = test_files / "with_links.md"
    test_file.write_text(test_content)

    file = SourceFile(path=test_file)
    config = ProcessingConfig()
    content = await process_file(file, config)
    assert "docs/test.md" in content
