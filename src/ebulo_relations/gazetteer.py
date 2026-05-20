"""Curated entities and Latin alias handling for the Ebulo text."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Entity:
    id: str
    label: str
    kind: str
    aliases: tuple[str, ...]


ENTITIES: tuple[Entity, ...] = (
    Entity("roger_ii", "Roger II of Sicily", "person", ("Roggerius", "Rogerus", "Roggerium")),
    Entity("robert_guiscard", "Robert Guiscard", "person", ("Guiscardi", "Guiscardus")),
    Entity("callistus_ii", "Callistus II", "person", ("Calisto", "Calistus")),
    Entity("albidia", "Albidia", "person", ("Albidia",)),
    Entity("sibilia", "Sibilia", "person", ("Sibilia",)),
    Entity("beatrix", "Beatrix", "person", ("Beatrix", "Beatricis")),
    Entity("constance", "Constance of Sicily", "person", ("Constantia", "Constancia", "Constantie")),
    Entity("henry_vi", "Henry VI", "person", ("Henricus", "Henrici", "Augustus", "Augusti", "Cesar", "Cesaris")),
    Entity("lucius_iii", "Lucius III", "person", ("Lucius",)),
    Entity("celestine_iii", "Celestine III", "person", ("Celestinus",)),
    Entity("william_ii", "William II of Sicily", "person", ("Wilelmi", "Wilelmus", "Guillelmus")),
    Entity("tancred", "Tancred of Sicily", "person", ("Tancredus", "Tancredum", "Tancrede", "Tancredi")),
    Entity("roger_andria", "Roger of Andria", "person", ("Rogerum", "Andria", "Andrie")),
    Entity("matthew_ajello", "Matthew of Ajello", "person", ("Matheus", "Mathei", "Scariothis")),
    Entity("walter_palermo", "Walter of Palermo", "person", ("Gualterius", "gualterizatur", "Panormi")),
    Entity("bartholomew", "Bartholomew", "person", ("Bartholomeus",)),
    Entity("urso", "Urso", "person", ("Urso",)),
    Entity("andronicus", "Andronicus", "person", ("Andronicus",)),
    Entity("alexius", "Alexius", "person", ("Alexi", "Alexius")),
    Entity("manuel", "Manuel I Komnenos", "person", ("Manuele", "Manuel")),
    Entity("frederick_i", "Frederick I Barbarossa", "person", ("Fredericus",)),
    Entity("charlemagne", "Charlemagne", "person", ("Carolus", "Carulos")),
    Entity("peter_apostle", "Saint Peter", "person", ("Petre", "Petrus")),
    Entity("octavian", "Octavian", "person", ("Octaviane", "Octavianus")),
    Entity("consanus", "Count Consanus", "person", ("Consanus",)),
    Entity("molisius", "Count Molisius", "person", ("Molisius",)),
    Entity("philippus", "Philippus", "person", ("Philippus",)),
    Entity("lupini", "Lupini brothers", "group", ("Lupini",)),
    Entity("rofridus", "Rofridus", "person", ("Rofridus",)),
    Entity("burellus", "Burellus", "person", ("Burellus",)),
    Entity("sicily", "Sicily", "place", ("Sicilia", "Sicilie", "Siculis", "Sicilidem")),
    Entity("palermo", "Palermo", "place", ("Panormum", "Panormi")),
    Entity("rome", "Rome", "place", ("Roma", "Romani")),
    Entity("apulia", "Apulia", "place", ("Apuliam",)),
    Entity("capua", "Capua", "place", ("Capuanus", "Capuane")),
    Entity("salerno", "Salerno", "place", ("Salerni",)),
    Entity("naples", "Naples", "place", ("Neapolis", "Parthenope")),
    Entity("monte_cassino", "Monte Cassino", "place", ("Casini",)),
    Entity("rocca_de_archis", "Rocca de Archis", "place", ("Rocca de Archis", "Archis")),
)

LATIN_ENDINGS = (
    "ibus",
    "orum",
    "arum",
    "ium",
    "ius",
    "us",
    "um",
    "am",
    "em",
    "is",
    "ae",
    "i",
    "o",
    "e",
    "a",
)


class Gazetteer:
    def __init__(self, entities: tuple[Entity, ...] = ENTITIES) -> None:
        self.entities = entities
        self._alias_to_id: dict[str, str] = {}
        self._stems_to_id: dict[str, str] = {}
        for entity in entities:
            for alias in (entity.label, *entity.aliases):
                key = fold(alias)
                self._alias_to_id[key] = entity.id
                self._stems_to_id[latin_stem(key)] = entity.id

    def get(self, entity_id: str) -> Entity:
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        raise KeyError(entity_id)

    def match_token(self, token: str) -> str | None:
        key = fold(token)
        if key in self._alias_to_id:
            return self._alias_to_id[key]
        return self._stems_to_id.get(latin_stem(key))

    def find_mentions(self, text: str) -> list[tuple[str, str]]:
        mentions: list[tuple[str, str]] = []
        seen_spans: set[tuple[int, int]] = set()
        for entity in self.entities:
            aliases = sorted(entity.aliases + (entity.label,), key=len, reverse=True)
            for alias in aliases:
                pattern = re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)", re.IGNORECASE)
                for match in pattern.finditer(text):
                    span = match.span()
                    if span not in seen_spans:
                        mentions.append((entity.id, match.group(0)))
                        seen_spans.add(span)
        return mentions


def fold(value: str) -> str:
    return re.sub(r"[^a-z]", "", value.lower().replace("j", "i").replace("v", "u"))


def latin_stem(value: str) -> str:
    value = fold(value)
    for ending in LATIN_ENDINGS:
        if len(value) > len(ending) + 3 and value.endswith(ending):
            return value[: -len(ending)]
    return value
