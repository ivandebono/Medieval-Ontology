"""High-level graph building API."""

from __future__ import annotations

from .extractor import extract_graph
from .graph import Graph
from .sources import DEFAULT_DOCUMENTS, DEFAULT_SOURCE_URL, Document, load_document, load_source
from .text import split_sections


def build_graph_from_text(
    text: str,
    min_weight: float = 1.0,
    document_id: str = "document",
    document_title: str = "Document",
) -> Graph:
    graph = extract_graph(split_sections(text), document_id=document_id, document_title=document_title)
    return graph.filtered(min_weight=min_weight)


def build_graph_from_source(source: str = DEFAULT_SOURCE_URL, min_weight: float = 1.0) -> Graph:
    return build_graph_from_text(load_source(source), min_weight=min_weight, document_id="source", document_title=source)


def build_graph_from_documents(
    documents: tuple[Document, ...] = DEFAULT_DOCUMENTS,
    min_weight: float = 1.0,
) -> Graph:
    graph = Graph()
    for document, text in (load_document(document) for document in documents):
        extract_graph(
            split_sections(text),
            graph=graph,
            document_id=document.id,
            document_title=document.title,
        )
    return graph.filtered(min_weight=min_weight)
