"""Entity and relation extraction."""

from __future__ import annotations

from itertools import combinations
import re

from .gazetteer import Gazetteer
from .graph import Graph
from .text import Section, split_sentences

TOKEN_RE = re.compile(r"\b[A-Z][A-Za-z<>\-']{2,}\b")

RELATION_PATTERNS: tuple[tuple[str, tuple[str, ...], float], ...] = (
    ("kinship", ("peperit", "natos", "natus", "patre", "patris", "matre", "matris", "prole", "avus", "soceri"), 4.0),
    ("marriage", ("coniux", "uxor", "nuberet", "nupta", "copulat", "iungit", "nuptu"), 4.0),
    ("succession", ("heres", "heredem", "succedat", "sceptra", "regnabis", "regnet", "regna"), 3.2),
    ("support", ("petit", "laudat", "iurat", "scripsit", "recepit", "fides", "vota"), 2.4),
    ("opposition", ("negat", "hostis", "captus", "obsessa", "resistit", "periura", "fraudis", "dolis"), 2.8),
    ("communication", ("epistola", "mitto", "scribo", "scripsit", "legatos", "verba"), 2.0),
    ("rule", ("rex", "regis", "regem", "imperatoris", "imperium", "Cesar", "Augustus", "coronatur"), 2.2),
)


def extract_graph(sections: list[Section], gazetteer: Gazetteer | None = None) -> Graph:
    gazetteer = gazetteer or Gazetteer()
    graph = Graph()

    for section in sections:
        section_mentions = _mentions(section.text, gazetteer)
        for entity_id in sorted(set(section_mentions)):
            entity = gazetteer.get(entity_id)
            graph.add_node(entity.id, entity.label, entity.kind, section.title)

        lines = [line.strip() for line in section.text.splitlines() if line.strip()]
        line_positions = [graph.add_source_line(line, section.title) for line in lines]
        for index, line in enumerate(lines):
            mentions = sorted(set(_mentions(line, gazetteer)))
            if not mentions:
                continue
            evidence = compact_evidence(line)
            for entity_id in mentions:
                graph.add_node_snippet(entity_id, evidence, section.title, line_positions[index])

        for sentence in split_sentences(section.text):
            mentions = sorted(set(_mentions(sentence, gazetteer)))
            if not mentions:
                continue
            evidence = compact_evidence(sentence)
            if len(mentions) < 2:
                continue
            relation, weight = classify_relation(sentence)
            for source, target in combinations(mentions, 2):
                graph.add_edge(source, target, relation, weight, evidence, section.title)

        for source, target in combinations(sorted(set(section_mentions)), 2):
            graph.add_edge(source, target, "co-occurrence", 0.25, section.title, section.title)

    return graph


def classify_relation(sentence: str) -> tuple[str, float]:
    folded = sentence.lower()
    best_relation = "co-occurrence"
    best_weight = 1.0
    for relation, cues, weight in RELATION_PATTERNS:
        if any(cue.lower() in folded for cue in cues):
            if weight > best_weight:
                best_relation = relation
                best_weight = weight
    return best_relation, best_weight


def compact_evidence(sentence: str, limit: int = 180) -> str:
    sentence = " ".join(sentence.split())
    if len(sentence) <= limit:
        return sentence
    return sentence[: limit - 3].rstrip() + "..."


def _mentions(text: str, gazetteer: Gazetteer) -> list[str]:
    matches = [entity_id for entity_id, _raw in gazetteer.find_mentions(text)]
    for token in TOKEN_RE.findall(text):
        entity_id = gazetteer.match_token(token)
        if entity_id:
            matches.append(entity_id)
    return matches
