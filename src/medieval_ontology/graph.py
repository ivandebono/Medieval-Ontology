"""Weighted graph model and exporters."""

from __future__ import annotations

from dataclasses import dataclass, field
import html
import json
import math
from pathlib import Path
from textwrap import dedent
from typing import Any

import networkx as nx
from pyvis.network import Network


@dataclass
class EvidenceSnippet:
    text: str
    section: str | None = None
    line_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "section": self.section,
            "lineIndex": self.line_index,
        }


@dataclass
class Node:
    id: str
    label: str
    kind: str = "unknown"
    count: int = 0
    sections: set[str] = field(default_factory=set)
    evidence: list[str] = field(default_factory=list)
    snippets: list[EvidenceSnippet] = field(default_factory=list)


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
        self.source_lines: list[dict[str, str]] = []

    def add_source_line(self, text: str, section: str | None = None) -> int:
        self.source_lines.append({"text": text, "section": section or ""})
        return len(self.source_lines) - 1

    def add_node(
        self,
        node_id: Any,
        label: str,
        kind: str = "unknown",
        section: str | None = None,
        evidence: str | None = None,
    ) -> None:
        node_id = str(node_id)
        node = self.nodes.setdefault(node_id, Node(id=node_id, label=label, kind=kind))
        node.count += 1
        if section:
            node.sections.add(section)
        if evidence and evidence not in node.evidence[:12]:
            node.evidence.append(evidence)

    def add_edge(
        self,
        source: Any,
        target: Any,
        relation: str,
        weight: float = 1.0,
        evidence: str | None = None,
        section: str | None = None,
    ) -> None:
        source = str(source)
        target = str(target)
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

    def add_node_evidence(self, node_id: Any, evidence: str, section: str | None = None) -> None:
        node_id = str(node_id)
        node = self.nodes.get(node_id)
        if not node:
            return
        if evidence and evidence not in node.evidence[:12]:
            node.evidence.append(evidence)
            node.snippets.append(EvidenceSnippet(text=evidence, section=section))
        if section:
            node.sections.add(section)

    def add_node_snippet(
        self,
        node_id: Any,
        text: str,
        section: str | None = None,
        line_index: int | None = None,
    ) -> None:
        node_id = str(node_id)
        node = self.nodes.get(node_id)
        if not node:
            return
        if text and all(snippet.line_index != line_index for snippet in node.snippets):
            node.evidence.append(text)
            node.snippets.append(
                EvidenceSnippet(
                    text=text,
                    section=section,
                    line_index=line_index,
                )
            )
            node.count = len(node.snippets)
        if section:
            node.sections.add(section)

    def filtered(self, min_weight: float = 1.0) -> "Graph":
        graph = Graph()
        graph.source_lines = list(self.source_lines)
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
                evidence=list(node.evidence),
                snippets=[
                    EvidenceSnippet(
                        text=snippet.text,
                        section=snippet.section,
                        line_index=snippet.line_index,
                    )
                    for snippet in node.snippets
                ],
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
                evidence=" | ".join(node.evidence[:6]),
                snippets=json.dumps([snippet.to_dict() for snippet in node.snippets[:6]], ensure_ascii=False),
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
                    "evidence": node.evidence,
                    "snippets": [snippet.to_dict() for snippet in node.snippets],
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
            title=_node_title(node),
            color=palette.get(node.kind, palette["unknown"]),
            value=max(6, node.count),
            snippets=[snippet.to_dict() for snippet in node.snippets[:10]],
            kind=node.kind,
            mentions=node.count,
        )
    for edge in graph.edges.values():
        title = f"{edge.relation}: {edge.weight:g}\n" + "\n".join(edge.evidence[:3])
        network.add_edge(edge.source, edge.target, value=edge.weight, title=title, label=edge.relation)

    body = network.generate_html(notebook=False)
    body = body.replace(
        "<body>",
        "<body><header style=\"font: 14px system-ui; padding: 16px 22px; background: #f6f1e8; color: #1f2933;\">"
        f"<h1 style=\"margin: 0; font-size: 24px;\">Liber ad Honorem Augusti Relationship Network</h1>"
        f"<p style=\"margin: 4px 0 0; color: #52606d;\">{len(graph.nodes)} entities, "
        f"{len(graph.edges)} weighted relationships. Click a node to inspect text snippets.</p></header>"
        f"{_inspector_markup()}",
    )
    return body.replace("</body>", f"{_inspector_script(graph.source_lines)}</body>")


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
  <h1>Liber ad Honorem Augusti Relationship Network</h1>
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


def _node_title(node: Node) -> str:
    snippets = "\n".join(node.evidence[:3])
    count_text = mention_label(node.count)
    if snippets:
        return f"{node.label}\n{node.kind}\n{node.count} {count_text}\n\n{snippets}"
    return f"{node.label}\n{node.kind}\n{node.count} {count_text}"


def mention_label(count: int) -> str:
    return "mention" if count == 1 else "mentions"


def _inspector_markup() -> str:
    return dedent(
        """
        <aside id="node-inspector" aria-live="polite">
          <div class="inspector-empty">Click a node to see where it appears in the text.</div>
        </aside>
        <style>
          body { overflow: hidden; }
          #mynetwork {
            width: calc(100% - 360px) !important;
            height: calc(100vh - 96px) !important;
            border: 0 !important;
          }
          .card {
            width: calc(100% - 360px) !important;
            border: 0 !important;
            border-radius: 0 !important;
          }
          #node-inspector {
            position: fixed;
            top: 84px;
            right: 0;
            bottom: 0;
            width: 360px;
            box-sizing: border-box;
            overflow: auto;
            padding: 18px;
            border-left: 1px solid #d8d1c4;
            background: #fffdf8;
            color: #1f2933;
            font: 14px system-ui, -apple-system, Segoe UI, sans-serif;
            box-shadow: -8px 0 24px rgba(31, 41, 51, 0.08);
          }
          #node-inspector h2 {
            margin: 0;
            font-size: 20px;
            line-height: 1.2;
          }
          #node-inspector .meta {
            margin: 6px 0 14px;
            color: #697586;
          }
          #node-inspector .context-control {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 0 0 14px;
            color: #52606d;
          }
          #node-inspector .context-control input {
            width: 58px;
            padding: 4px 6px;
            border: 1px solid #c9c0b2;
            border-radius: 4px;
            background: #fffdf8;
            color: #1f2933;
          }
          #node-inspector .snippet {
            display: block;
            width: 100%;
            text-align: left;
            margin: 0 0 12px;
            padding: 12px;
            border-left: 3px solid #2f6f73;
            border-top: 0;
            border-right: 0;
            border-bottom: 0;
            background: #f6f1e8;
            color: #1f2933;
            cursor: pointer;
            font: inherit;
            line-height: 1.45;
          }
          #node-inspector .snippet:hover,
          #node-inspector .snippet:focus {
            background: #efe6d7;
            outline: 2px solid rgba(47, 111, 115, 0.24);
          }
          #node-inspector .context {
            margin: -6px 0 14px;
            padding: 10px 12px;
            background: #fff8ec;
            border: 1px solid #e4dac9;
            white-space: pre-wrap;
            line-height: 1.45;
          }
          #node-inspector .context .focus-line {
            font-weight: 700;
            color: #1f2933;
          }
          #node-inspector .section {
            margin-bottom: 6px;
            color: #697586;
            font-size: 12px;
          }
          #node-inspector .inspector-empty {
            color: #697586;
            line-height: 1.45;
          }
          @media (max-width: 820px) {
            body { overflow: auto; }
            #mynetwork, .card { width: 100% !important; height: 68vh !important; }
            #node-inspector {
              position: static;
              width: 100%;
              max-height: none;
              border-left: 0;
              border-top: 1px solid #d8d1c4;
              box-shadow: none;
            }
          }
        </style>
        """
    )


def _inspector_script(source_lines: list[dict[str, str]]) -> str:
    source_lines_json = json.dumps(source_lines, ensure_ascii=False)
    return dedent(
        """
        <script>
          (function () {
            var sourceLines = __SOURCE_LINES__;

            function escapeHtml(value) {
              return String(value || "").replace(/[&<>"']/g, function (character) {
                return {
                  "&": "&amp;",
                  "<": "&lt;",
                  ">": "&gt;",
                  '"': "&quot;",
                  "'": "&#39;"
                }[character];
              });
            }

            function mentionLabel(count) {
              return count === 1 ? "mention" : "mentions";
            }

            function renderNodeInspector(nodeId) {
              var panel = document.getElementById("node-inspector");
              if (!panel || !nodeId || typeof nodes === "undefined") {
                return;
              }
              var node = nodes.get(nodeId);
              if (!node) {
                return;
              }
              var snippets = node.snippets || [];
              var contextSize = 5;
              var snippetHtml = snippets.length
                ? snippets.map(function (snippet) {
                    var text = typeof snippet === "string" ? snippet : snippet.text;
                    return '<button class="snippet" type="button">' + escapeHtml(text) + "</button>";
                  }).join("")
                : '<div class="inspector-empty">No sentence-level snippet was captured for this node.</div>';
              panel.innerHTML =
                "<h2>" + escapeHtml(node.label) + "</h2>" +
                '<div class="meta">' + escapeHtml(node.kind || "entity") + " · " +
                escapeHtml(node.mentions || 0) + " " + mentionLabel(node.mentions || 0) + "</div>" +
                '<label class="context-control">Context lines <input id="context-size" type="number" min="0" max="20" value="' +
                contextSize + '"></label>' +
                snippetHtml;

              panel.querySelectorAll(".snippet").forEach(function (button, index) {
                button.addEventListener("click", function () {
                  var input = document.getElementById("context-size");
                  var size = Math.max(0, Math.min(20, parseInt(input && input.value, 10) || 0));
                  renderSnippetContext(button, snippets[index], size);
                });
              });
            }

            function renderSnippetContext(button, snippet, contextSize) {
              var existing = button.nextElementSibling;
              if (existing && existing.className === "context") {
                existing.remove();
                return;
              }
              var data = typeof snippet === "string" ? { text: snippet, lineIndex: null } : snippet;
              var lineIndex = Number.isInteger(data.lineIndex) ? data.lineIndex : -1;
              var start = Math.max(0, lineIndex - contextSize);
              var end = Math.min(sourceLines.length - 1, lineIndex + contextSize);
              var section = data.section || "";
              var lines = [];
              if (section) {
                lines.push('<div class="section">' + escapeHtml(section) + "</div>");
              }
              if (lineIndex < 0 || !sourceLines[lineIndex]) {
                lines.push('<span class="focus-line">' + escapeHtml(data.text || "") + "</span>");
              } else {
                for (var index = start; index <= end; index += 1) {
                  var line = sourceLines[index] || { text: "" };
                  var className = index === lineIndex ? ' class="focus-line"' : "";
                  lines.push("<span" + className + ">" + escapeHtml(line.text) + "</span>");
                }
              }
              var context = document.createElement("div");
              context.className = "context";
              context.innerHTML = lines.filter(Boolean).join("<br>");
              button.insertAdjacentElement("afterend", context);
            }

            var attachInspector = setInterval(function () {
              if (typeof network !== "undefined" && typeof nodes !== "undefined") {
                clearInterval(attachInspector);
                network.on("click", function (params) {
                  if (params.nodes && params.nodes.length) {
                    renderNodeInspector(params.nodes[0]);
                  }
                });
              }
            }, 100);
          }());
        </script>
        """
    ).replace("__SOURCE_LINES__", source_lines_json)
