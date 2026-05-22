"""Curated entities and Latin alias handling for the Ebulo text."""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import quote_plus
from uuid import UUID, uuid5


@dataclass(frozen=True)
class Entity:
    key: str
    label: str
    kind: str
    aliases: tuple[str, ...]

    @property
    def id(self) -> UUID:
        return uuid5(ENTITY_NAMESPACE, self.key)

    @property
    def wikipedia_url(self) -> str:
        return WIKIPEDIA_URLS.get(self.key, wikipedia_search_url(self.label))


ENTITY_NAMESPACE = UUID("8ed8a50d-058e-4da2-9f1d-6b496df15502")


WIKIPEDIA_URLS: dict[str, str] = {
    "roger_ii": "https://en.wikipedia.org/wiki/Roger_II_of_Sicily",
    "robert_guiscard": "https://en.wikipedia.org/wiki/Robert_Guiscard",
    "callistus_ii": "https://en.wikipedia.org/wiki/Pope_Callistus_II",
    "beatrix": "https://en.wikipedia.org/wiki/Beatrice_of_Rethel",
    "constance": "https://en.wikipedia.org/wiki/Constance_of_Sicily,_Holy_Roman_Empress",
    "henry_vi": "https://en.wikipedia.org/wiki/Henry_VI,_Holy_Roman_Emperor",
    "lucius_iii": "https://en.wikipedia.org/wiki/Pope_Lucius_III",
    "celestine_iii": "https://en.wikipedia.org/wiki/Pope_Celestine_III",
    "william_ii": "https://en.wikipedia.org/wiki/William_II_of_Sicily",
    "tancred": "https://en.wikipedia.org/wiki/Tancred,_King_of_Sicily",
    "matthew_ajello": "https://en.wikipedia.org/wiki/Matthew_of_Ajello",
    "manuel": "https://en.wikipedia.org/wiki/Manuel_I_Komnenos",
    "frederick_i": "https://en.wikipedia.org/wiki/Frederick_Barbarossa",
    "charlemagne": "https://en.wikipedia.org/wiki/Charlemagne",
    "peter_apostle": "https://en.wikipedia.org/wiki/Saint_Peter",
    "octavian": "https://en.wikipedia.org/wiki/Octavian",
    "sicily": "https://en.wikipedia.org/wiki/Sicily",
    "palermo": "https://en.wikipedia.org/wiki/Palermo",
    "rome": "https://en.wikipedia.org/wiki/Rome",
    "apulia": "https://en.wikipedia.org/wiki/Apulia",
    "capua": "https://en.wikipedia.org/wiki/Capua",
    "salerno": "https://en.wikipedia.org/wiki/Salerno",
    "naples": "https://en.wikipedia.org/wiki/Naples",
    "monte_cassino": "https://en.wikipedia.org/wiki/Monte_Cassino",
}


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
        self._alias_to_id: dict[str, UUID] = {}
        self._stems_to_id: dict[str, UUID] = {}
        for entity in entities:
            for alias in (entity.label, *entity.aliases):
                key = fold(alias)
                self._alias_to_id[key] = entity.id
                self._stems_to_id[latin_stem(key)] = entity.id

    def get(self, entity_id: str | UUID) -> Entity:
        for entity in self.entities:
            if entity.id == entity_id or str(entity.id) == str(entity_id) or entity.key == entity_id:
                return entity
        raise KeyError(entity_id)

    def match_token(self, token: str) -> UUID | None:
        key = fold(token)
        if key in self._alias_to_id:
            return self._alias_to_id[key]
        return self._stems_to_id.get(latin_stem(key))

    def find_mentions(self, text: str) -> list[tuple[UUID, str]]:
        mentions: list[tuple[UUID, str]] = []
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


def wikipedia_search_url(label: str) -> str:
    return f"https://en.wikipedia.org/w/index.php?search={quote_plus(label)}"
