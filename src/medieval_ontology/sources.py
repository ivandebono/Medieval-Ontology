"""Source loading for local files and remote text pages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DEFAULT_SOURCE_URL = "https://www.thelatinlibrary.com/ebulo.html"
FALCANDUS_SOURCE_URL = "https://www.thelatinlibrary.com/falcandus.html"
DEFAULT_DOCUMENTS_DIR = Path("texts")


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    source: str


DEFAULT_DOCUMENTS: tuple[Document, ...] = (
    Document(
        id="ebulo",
        title="Liber ad Honorem Augusti",
        source=DEFAULT_SOURCE_URL,
    ),
    Document(
        id="falcandus",
        title="Liber de Regno Sicilie",
        source=FALCANDUS_SOURCE_URL,
    ),
)


def cached_documents(
    directory: Path | str = DEFAULT_DOCUMENTS_DIR,
    documents: tuple[Document, ...] = DEFAULT_DOCUMENTS,
) -> tuple[Document, ...]:
    directory = Path(directory)
    return tuple(
        Document(
            id=document.id,
            title=document.title,
            source=str(cached_document_path(directory, document)),
        )
        for document in documents
    )


def cached_document_path(directory: Path | str, document: Document) -> Path:
    return Path(directory) / f"{document.id}.txt"


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = []
    for raw_line in text.replace("\xa0", " ").splitlines():
        line = " ".join(raw_line.split())
        if line:
            lines.append(line)
    return "\n".join(lines)


def load_source(source: str = DEFAULT_SOURCE_URL, timeout: float = 30.0) -> str:
    """Load text from a URL or local path, stripping HTML when necessary."""

    if source.startswith(("http://", "https://")):
        response = requests.get(source, timeout=timeout, headers={"User-Agent": "ontology/0.1"})
        response.raise_for_status()
        content = response.text
    else:
        content = Path(source).read_text(encoding="utf-8")

    if "<html" in content.lower() or "<br" in content.lower() or "<p" in content.lower():
        return html_to_text(content)
    return content


def load_document(document: Document, timeout: float = 30.0) -> tuple[Document, str]:
    return document, load_source(document.source, timeout=timeout)


def save_documents(
    directory: Path | str = DEFAULT_DOCUMENTS_DIR,
    documents: tuple[Document, ...] = DEFAULT_DOCUMENTS,
    refresh: bool = False,
    timeout: float = 30.0,
) -> list[Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for document in documents:
        path = cached_document_path(directory, document)
        if refresh or not path.exists():
            _document, text = load_document(document, timeout=timeout)
            path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths
