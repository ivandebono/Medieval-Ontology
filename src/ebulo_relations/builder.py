"""High-level graph building API."""

from __future__ import annotations

from .extractor import extract_graph
from .graph import Graph
from .sources import DEFAULT_SOURCE_URL, load_source
from .text import split_sections


def build_graph_from_text(text: str, min_weight: float = 1.0) -> Graph:
    graph = extract_graph(split_sections(text))
    return graph.filtered(min_weight=min_weight)


def build_graph_from_source(source: str = DEFAULT_SOURCE_URL, min_weight: float = 1.0) -> Graph:
    return build_graph_from_text(load_source(source), min_weight=min_weight)
