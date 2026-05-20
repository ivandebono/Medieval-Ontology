"""Weighted graph model and exporters."""

from __future__ import annotations

from dataclasses import dataclass, field
import html
import json
import math
from pathlib import Path

import networkx as nx
from pyvis.network import Network


@dataclass
class Node:
    id: str
    label: str
    kind: str = "unknown"
    count: int = 0
    sections: set[str] = field(default_factory=set)


@dataclass
class Edge:
    source: str
    target: str
    relation: str
    weight: float = 1.0
    evidence: list[str] = field(default_factory=list)
    sections: set[str] = field(default_factory=set)


class Graph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[tuple[str, str, str], Edge] = {}

    def add_node(self, node_id: str, label: str, kind: str = "unknown", section: str | None = None) -> None:
        node = self.nodes.setdefault(node_id, Node(id=node_id, label=label, kind=kind))
        node.count += 1
        if section:
            node.sections.add(section)

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        weight: float = 1.0,
        evidence: str | None = None,
        section: str | None = None,
    ) -> None:
        if source == target:
            return
        left, right = sorted((source, target))
        key = (left, right, relation)
        edge = self.edges.setdefault(key, Edge(source=left, target=right, relation=relation))
        edge.weight += weight
        if evidence and evidence not in edge.evidence[:8]:
            edge.evidence.append(evidence)
        if section:
            edge.sections.add(section)

    def filtered(self, min_weight: float = 1.0) -> "Graph":
        graph = Graph()
        kept_nodes: set[str] = set()
        for edge in self.edges.values():
            if edge.weight >= min_weight:
                kept_nodes.update((edge.source, edge.target))
                graph.edges[(edge.source, edge.target, edge.relation)] = Edge(
                    source=edge.source,
                    target=edge.target,
                    relation=edge.relation,
                    weight=edge.weight,
                    evidence=list(edge.evidence),
                    sections=set(edge.sections),
                )
        for node_id in kept_nodes:
            node = self.nodes[node_id]
            graph.nodes[node_id] = Node(
                id=node.id,
                label=node.label,
                kind=node.kind,
                count=node.count,
                sections=set(node.sections),
            )
        return graph

    def top_nodes(self, limit: int = 10) -> list[tuple[str, float]]:
        scores = {node_id: 0.0 for node_id in self.nodes}
        for edge in self.edges.values():
            scores[edge.source] = scores.get(edge.source, 0.0) + edge.weight
            scores[edge.target] = scores.get(edge.target, 0.0) + edge.weight
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [(self.nodes[node_id].label, score) for node_id, score in ranked[:limit]]

    def to_networkx(self, multigraph: bool = True) -> nx.Graph:
        graph: nx.Graph = nx.MultiGraph() if multigraph else nx.Graph()
        for node in self.nodes.values():
            graph.add_node(
                node.id,
                label=node.label,
                kind=node.kind,
                count=node.count,
                sections=" | ".join(sorted(node.sections)),
            )
        for edge in self.edges.values():
            graph.add_edge(
                edge.source,
                edge.target,
                relation=edge.relation,
                weight=edge.weight,
                evidence=" | ".join(edge.evidence[:4]),
                sections=" | ".join(sorted(edge.sections)),
            )
        return graph

    def to_json(self) -> str:
        payload = {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "kind": node.kind,
                    "count": node.count,
                    "sections": sorted(node.sections),
                }
                for node in sorted(self.nodes.values(), key=lambda item: item.label)
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "relation": edge.relation,
                    "weight": round(edge.weight, 3),
                    "sections": sorted(edge.sections),
                    "evidence": edge.evidence,
                }
                for edge in sorted(self.edges.values(), key=lambda item: (-item.weight, item.source, item.target))
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def to_dot(self) -> str:
        lines = ["graph ebulo {"]
        for node in self.nodes.values():
            lines.append(f'  "{node.id}" [label="{_esc(node.label)}"];')
        for edge in self.edges.values():
            label = f"{edge.relation} ({edge.weight:g})"
            lines.append(f'  "{edge.source}" -- "{edge.target}" [label="{_esc(label)}"];')
        lines.append("}")
        return "\n".join(lines)

    def to_graphml(self) -> str:
        return "\n".join(nx.generate_graphml(self.to_networkx(multigraph=True)))

    def to_html(self) -> str:
        return render_html(self)

    def write(self, path: str | Path, format: str = "json") -> None:
        format = format.lower()
        renderers = {
            "json": self.to_json,
            "dot": self.to_dot,
            "graphml": self.to_graphml,
            "html": self.to_html,
        }
        if format not in renderers:
            raise ValueError(f"Unsupported format: {format}")
        Path(path).write_text(renderers[format](), encoding="utf-8")


def render_html(graph: Graph) -> str:
    if graph.nodes:
        return render_pyvis_html(graph)
    return "<!doctype html><title>Ebulo Relationship Network</title><p>No graph data.</p>"


def render_pyvis_html(graph: Graph) -> str:
    network = Network(
        height="760px",
        width="100%",
        bgcolor="#fbfaf6",
        font_color="#1f2933",
        cdn_resources="in_line",
    )
    network.barnes_hut(gravity=-28000, central_gravity=0.18, spring_length=170, spring_strength=0.035)

    palette = {"person": "#2f6f73", "place": "#9b5c2e", "group": "#6f579f", "unknown": "#455a64"}
    for node in graph.nodes.values():
        network.add_node(
            node.id,
            label=node.label,
            title=f"{html.escape(node.label)}<br>{node.kind}<br>{node.count} mentions",
            color=palette.get(node.kind, palette["unknown"]),
            value=max(6, node.count),
        )
    for edge in graph.edges.values():
        title = html.escape(f"{edge.relation}: {edge.weight:g}\n" + "\n".join(edge.evidence[:3]))
        network.add_edge(edge.source, edge.target, value=edge.weight, title=title, label=edge.relation)

    body = network.generate_html(notebook=False)
    return body.replace(
        "<body>",
        "<body><header style=\"font: 14px system-ui; padding: 16px 22px; background: #f6f1e8; color: #1f2933;\">"
        f"<h1 style=\"margin: 0; font-size: 24px;\">Petrus de Ebulo Relationship Network</h1>"
        f"<p style=\"margin: 4px 0 0; color: #52606d;\">{len(graph.nodes)} entities, "
        f"{len(graph.edges)} weighted relationships. Drag nodes, zoom, and hover for evidence.</p></header>",
    )


def render_svg_html(graph: Graph) -> str:
    width, height = 1200, 820
    positions = _layout(graph, width, height)
    max_weight = max((edge.weight for edge in graph.edges.values()), default=1.0)
    edges = []
    for edge in graph.edges.values():
        x1, y1 = positions[edge.source]
        x2, y2 = positions[edge.target]
        stroke = 1.0 + 5.0 * edge.weight / max_weight
        title = html.escape(f"{edge.relation}: {edge.weight:g}\n" + "\n".join(edge.evidence[:2]))
        edges.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#78909c" stroke-width="{stroke:.2f}" opacity="0.58"><title>{title}</title></line>'
        )
    nodes = []
    for node in graph.nodes.values():
        x, y = positions[node.id]
        radius = 8 + min(18, node.count * 1.7)
        fill = {"person": "#2f6f73", "place": "#9b5c2e", "group": "#6f579f"}.get(node.kind, "#455a64")
        nodes.append(
            f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" opacity="0.94">'
            f"<title>{html.escape(node.label)} ({node.kind})</title></circle>"
            f'<text x="{x + radius + 4:.1f}" y="{y + 4:.1f}">{html.escape(node.label)}</text></g>'
        )
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Ebulo Relationship Network</title>
<style>
body {{ margin: 0; font: 14px system-ui, -apple-system, Segoe UI, sans-serif; color: #1f2933; background: #f6f1e8; }}
header {{ padding: 18px 28px 10px; }}
h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
p {{ margin: 6px 0 0; color: #52606d; }}
svg {{ display: block; width: 100vw; height: calc(100vh - 76px); background: #fbfaf6; }}
text {{ paint-order: stroke; stroke: #fbfaf6; stroke-width: 4px; fill: #1f2933; font-size: 12px; }}
</style>
<header>
  <h1>Petrus de Ebulo Relationship Network</h1>
  <p>{len(graph.nodes)} entities, {len(graph.edges)} weighted relationships. Hover nodes and edges for details.</p>
</header>
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Relationship network graph">
  <g>{''.join(edges)}</g>
  <g>{''.join(nodes)}</g>
</svg>
</html>
"""


def _layout(graph: Graph, width: int, height: int) -> dict[str, tuple[float, float]]:
    center_x, center_y = width / 2, height / 2
    radius_x, radius_y = width * 0.39, height * 0.38
    ranked = graph.top_nodes(len(graph.nodes))
    order = [next(node.id for node in graph.nodes.values() if node.label == label) for label, _score in ranked]
    positions: dict[str, tuple[float, float]] = {}
    total = max(1, len(order))
    for index, node_id in enumerate(order):
        angle = 2 * math.pi * index / total
        ring = 0.72 + 0.28 * (index % 3) / 2
        positions[node_id] = (
            center_x + math.cos(angle) * radius_x * ring,
            center_y + math.sin(angle) * radius_y * ring,
        )
    return positions


def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
