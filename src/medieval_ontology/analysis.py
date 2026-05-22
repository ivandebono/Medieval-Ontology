"""Graph-structure analysis helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from .graph import Graph


def graph_structure_insights(graph: Graph, top_n: int = 10) -> dict[str, Any]:
    """Compute structural graph metrics without changing visualization output."""

    raw_network = _network_from_graph(graph)
    return network_structure_insights(raw_network, top_n=top_n)


def graphml_structure_insights(path: str | Path, top_n: int = 10) -> dict[str, Any]:
    return network_structure_insights(nx.read_graphml(path), top_n=top_n)


def network_structure_insights(raw_network: nx.Graph, top_n: int = 10) -> dict[str, Any]:
    network = _simple_network(raw_network)
    components = [sorted(component) for component in nx.connected_components(network)] if network.nodes else []
    largest_component = network.subgraph(max(components, key=len)).copy() if components else network.copy()
    degree_centrality = nx.degree_centrality(network)
    betweenness_centrality = nx.betweenness_centrality(network, weight="weight") if network.nodes else {}
    closeness_centrality = nx.closeness_centrality(network) if network.nodes else {}
    clustering = nx.clustering(network) if network.nodes else {}

    summary: dict[str, Any] = {
        "nodeCount": network.number_of_nodes(),
        "edgeCount": raw_network.number_of_edges(),
        "simpleEdgeCount": network.number_of_edges(),
        "density": round(nx.density(network), 6),
        "connectedComponentCount": len(components),
        "largestComponentSize": largest_component.number_of_nodes(),
        "averageClustering": round(nx.average_clustering(network), 6) if network.nodes else 0.0,
        "transitivity": round(nx.transitivity(network), 6) if network.nodes else 0.0,
    }
    if largest_component.number_of_nodes() > 1:
        summary["averageShortestPathLengthLargestComponent"] = round(
            nx.average_shortest_path_length(largest_component),
            6,
        )
        summary["diameterLargestComponent"] = nx.diameter(largest_component)

    return {
        "summary": summary,
        "relations": _relation_counts(raw_network),
        "topDegreeCentrality": _rank_nodes(network, degree_centrality, top_n),
        "topWeightedDegree": _rank_nodes(network, dict(network.degree(weight="weight")), top_n),
        "topBetweennessCentrality": _rank_nodes(network, betweenness_centrality, top_n),
        "topClosenessCentrality": _rank_nodes(network, closeness_centrality, top_n),
        "topClustering": _rank_nodes(network, clustering, top_n),
        "connectedComponents": [
            {
                "size": len(component),
                "nodes": [_node_label(network, node_id) for node_id in component],
            }
            for component in sorted(components, key=len, reverse=True)
        ],
    }


def write_graph_structure_insights(graph: Graph, path: str | Path, top_n: int = 10) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(graph_structure_insights(graph, top_n=top_n), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_graphml_structure_insights(graphml_path: str | Path, output_path: str | Path, top_n: int = 10) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(graphml_structure_insights(graphml_path, top_n=top_n), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _network_from_graph(graph: Graph) -> nx.MultiGraph:
    network = nx.MultiGraph()
    for node in graph.nodes.values():
        network.add_node(node.id, label=node.label, kind=node.kind, count=node.count)
    for edge in graph.edges.values():
        network.add_edge(edge.source, edge.target, weight=edge.weight, relation=edge.relation)
    return network


def _simple_network(raw_network: nx.Graph) -> nx.Graph:
    network = nx.Graph()
    for node_id, data in raw_network.nodes(data=True):
        network.add_node(str(node_id), **dict(data))
    for source, target, data in _edges(raw_network):
        source = str(source)
        target = str(target)
        weight = _edge_weight(data)
        relation = str(data.get("relation", "unknown"))
        if network.has_edge(source, target):
            network[source][target]["weight"] += weight
            network[source][target]["relations"].add(relation)
        else:
            network.add_edge(source, target, weight=weight, relations={relation})
    return network


def _rank_nodes(network: nx.Graph, values: dict[str, float], limit: int) -> list[dict[str, Any]]:
    return [
        {
            "id": node_id,
            "label": _node_label(network, node_id),
            "value": round(value, 6),
        }
        for node_id, value in sorted(values.items(), key=lambda item: (-item[1], _node_label(network, item[0])))[:limit]
    ]


def _relation_counts(network: nx.Graph) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, float]] = {}
    for _source, _target, data in _edges(network):
        relation = str(data.get("relation", "unknown"))
        entry = counts.setdefault(relation, {"edgeCount": 0, "totalWeight": 0.0})
        entry["edgeCount"] += 1
        entry["totalWeight"] += _edge_weight(data)
    return [
        {
            "relation": relation,
            "edgeCount": int(values["edgeCount"]),
            "totalWeight": round(values["totalWeight"], 3),
        }
        for relation, values in sorted(counts.items(), key=lambda item: (-item[1]["totalWeight"], item[0]))
    ]


def _edges(network: nx.Graph) -> list[tuple[Any, Any, dict[str, Any]]]:
    if network.is_multigraph():
        return [(source, target, data) for source, target, _key, data in network.edges(keys=True, data=True)]
    return [(source, target, data) for source, target, data in network.edges(data=True)]


def _edge_weight(data: dict[str, Any]) -> float:
    try:
        return float(data.get("weight", 1.0))
    except (TypeError, ValueError):
        return 1.0


def _node_label(network: nx.Graph, node_id: str) -> str:
    return str(network.nodes.get(node_id, {}).get("label") or node_id)
