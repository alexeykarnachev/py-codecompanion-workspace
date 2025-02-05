import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

import aiofiles
import httpx
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


@dataclass
class Document:
    path: str
    content: str
    level: int


class DocCombiner:
    def __init__(self) -> None:
        self.console = Console()
        self.client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
        self.documents: list[Document] = []

    async def fetch_markdown_files(self, url: str) -> list[str]:
        """Fetch list of markdown files from a GitHub directory"""
        # Convert regular GitHub URL to API URL
        if "github.com" in url:
            parts = url.split("github.com/")[1].split("/")
            owner, repo = parts[0:2]
            min_parts_for_path = 4
            path = (
                "/".join(parts[min_parts_for_path:])
                if len(parts) > min_parts_for_path
                else ""
            )
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

            response = await self.client.get(api_url)
            response.raise_for_status()

            files = []
            for item in response.json():
                if item["type"] == "file" and item["name"].endswith(".md"):
                    files.append(item["download_url"])
                elif item["type"] == "dir" and not any(
                    skip in item["path"] for skip in ["assets", "js", "stylesheets"]
                ):
                    subfiles = await self.fetch_markdown_files(item["html_url"])
                    files.extend(subfiles)
            return files
        return []

    async def process_url(self, url: str) -> None:
        """Process URL source"""
        if "github.com" in url:
            # Handle GitHub repository
            markdown_files = await self.fetch_markdown_files(url)
            for file_url in markdown_files:
                content = await self.client.get(file_url)
                content.raise_for_status()

                # Calculate level based on path depth
                path_parts = urlparse(file_url).path.split("/")
                level = len([p for p in path_parts if p and p not in ["blob", "raw"]])

                self.documents.append(
                    Document(path=file_url, content=content.text, level=level)
                )
        else:
            # Handle direct markdown URL
            content = await self.client.get(url)
            content.raise_for_status()
            self.documents.append(Document(path=url, content=content.text, level=1))

    async def process_local_directory(self, path: Path) -> None:
        """Process local directory recursively"""
        for file_path in sorted(path.rglob("*.md")):
            if any(
                skip in str(file_path) for skip in ["assets/", "js/", "stylesheets/"]
            ):
                continue

            level = len(file_path.relative_to(path).parts)
            async with aiofiles.open(file_path) as f:
                content = await f.read()

            self.documents.append(
                Document(path=str(file_path), content=content, level=level)
            )

    def adjust_content(
        self, content: str, base_level: int, base_url: str | None = None
    ) -> str:
        """Adjust headers and links in content"""
        lines = content.split("\n")
        adjusted_lines = []

        for original_line in lines:
            current_line = original_line
            # Adjust headers
            if current_line.strip().startswith("#"):
                current_line = "#" * base_level + current_line.lstrip("#")

            # Adjust links if base_url is provided
            if base_url and "[" in current_line and "](" in current_line:
                current_line = re.sub(
                    r"\[(.*?)\]\((.*?)\)",
                    lambda m: f"[{m.group(1)}]({urljoin(base_url, m.group(2))})",
                    current_line,
                )

            adjusted_lines.append(current_line)

        return "\n".join(adjusted_lines)

    async def combine_docs(self, source: str, output: Path) -> None:
        """Main method to combine documentation"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Processing documentation...", total=None)

            try:
                if source.startswith(("http://", "https://")):
                    # Handle remote URL
                    await self.process_url(source)
                else:
                    # Handle local directory
                    source_path = Path(source)
                    if not source_path.exists():
                        raise typer.BadParameter(f"Source path {source} does not exist")
                    await self.process_local_directory(source_path)

                # Combine all documents
                combined_content = []
                for doc in sorted(self.documents, key=lambda x: x.path):
                    section_name = Path(doc.path).stem.replace("-", " ").title()
                    combined_content.append(f"\n{'#' * doc.level} {section_name}\n")
                    combined_content.append(
                        self.adjust_content(
                            doc.content,
                            doc.level,
                            base_url=(
                                source
                                if source.startswith(("http://", "https://"))
                                else None
                            ),
                        )
                    )

                # Write output
                async with aiofiles.open(output, "w", encoding="utf-8") as f:
                    await f.write("\n".join(combined_content))

            finally:
                await self.client.aclose()
                progress.update(task, completed=True)


def main(
    source: str = typer.Argument(
        ...,
        help="Source directory or URL (e.g., './docs' or 'https://github.com/user/repo/tree/main/docs')",
    ),
    output: str = typer.Option("complete_docs.md", help="Output file path"),
) -> None:
    """
    Combine markdown documentation from a directory or URL into a single file.

    Examples:
        Local directory:   ./doc_combiner.py ./docs
        GitHub docs:       ./doc_combiner.py https://github.com/username/repo/tree/main/docs
        Custom output:     ./doc_combiner.py ./docs --output combined.md
    """
    asyncio.run(DocCombiner().combine_docs(source, Path(output)))
    Console().print(f"✨ Documentation combined successfully into {output}")


if __name__ == "__main__":
    typer.run(main)
