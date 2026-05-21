"""Command line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .builder import build_graph_from_documents, build_graph_from_source
from .gazetteer import Gazetteer
from .sources import (
    DEFAULT_DOCUMENTS,
    DEFAULT_DOCUMENTS_DIR,
    cached_document_path,
    cached_documents,
    load_document,
    load_source,
    save_documents,
)
from .text import split_sections

app = typer.Typer(
    add_completion=False,
    help="Build relationship network graphs from Petrus de Ebulo's Liber ad honorem Augusti.",
)
console = Console()


@app.command()
def build(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="URL or local file to parse. Defaults to all built-in documents."),
    documents_dir: Optional[Path] = typer.Option(None, "--documents-dir", help="Directory containing saved built-in document text files."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output path. Defaults to stdout."),
    format: str = typer.Option("json", "--format", "-f", help="json, graphml, dot, or html."),
    min_weight: float = typer.Option(1.0, "--min-weight", help="Drop edges below this weight."),
) -> None:
    """Build and export a relationship graph."""

    documents = cached_documents(documents_dir) if documents_dir else DEFAULT_DOCUMENTS
    graph = (
        build_graph_from_source(source, min_weight=min_weight)
        if source
        else build_graph_from_documents(documents=documents, min_weight=min_weight)
    )
    renderers = {
        "json": graph.to_json,
        "graphml": graph.to_graphml,
        "dot": graph.to_dot,
        "html": graph.to_html,
    }
    if format not in renderers:
        raise typer.BadParameter("format must be one of: json, graphml, dot, html")

    rendered = renderers[format]()
    if output:
        output.write_text(rendered, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {len(graph.nodes)} nodes and {len(graph.edges)} edges to {output}")
    else:
        console.print(rendered)


@app.command()
def entities(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="URL or local file to parse. Defaults to all built-in documents."),
    documents_dir: Optional[Path] = typer.Option(None, "--documents-dir", help="Directory containing saved built-in document text files."),
    limit: int = typer.Option(25, "--limit", "-n", help="Maximum number of entities to show."),
) -> None:
    """List the most frequently recognized entities."""

    gazetteer = Gazetteer()
    counts: dict[str, int] = {}
    if source:
        texts = [(source, load_source(source))]
    else:
        documents = cached_documents(documents_dir) if documents_dir else DEFAULT_DOCUMENTS
        texts = [(document.title, text) for document, text in (load_document(document) for document in documents)]
    for _title, text in texts:
        for section in split_sections(text):
            for entity_id, _raw in gazetteer.find_mentions(section.text):
                counts[entity_id] = counts.get(entity_id, 0) + 1

    table = Table(title="Recognized Entities")
    table.add_column("Mentions", justify="right")
    table.add_column("Entity")
    table.add_column("Kind")
    for entity_id, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]:
        entity = gazetteer.get(entity_id)
        table.add_row(str(count), entity.label, entity.kind)
    console.print(table)


@app.command("cache-sources")
def cache_sources(
    output: Path = typer.Option(DEFAULT_DOCUMENTS_DIR, "--output", "-o", help="Directory for saved text files."),
    refresh: bool = typer.Option(False, "--refresh", help="Fetch and overwrite existing saved text files."),
) -> None:
    """Fetch the built-in documents and save normalized text files."""

    existing_paths = {
        cached_document_path(output, document)
        for document in DEFAULT_DOCUMENTS
        if cached_document_path(output, document).exists()
    }
    paths = save_documents(output, refresh=refresh)
    for path in paths:
        action = "Saved" if refresh or path not in existing_paths else "Using"
        console.print(f"[green]{action}[/green] {path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
