from ebulo_relations import build_graph_from_text
from ebulo_relations.gazetteer import Gazetteer
from ebulo_relations.sources import html_to_text
from ebulo_relations.text import split_sections


SAMPLE = """
PETRUS DE EBULO
LIBER AD HONOREM AUGUSTI SIVE DE REBUS SICULIS
Traditur Augusto coniux Constantia magno;
Lucius in nuptu pronuba causa fuit.
Particula VI.: Epistola ad Tancredum
Hanc tibi Matheus mitto Tancrede salutem.
Per me regnabis, per me tibi regna dabuntur.
Particula XI.: Regni legatio
Scripsit Consanus, scripsit Molisius, scripsit et antistes Panormi.
"""


def test_html_to_text_strips_tags():
    assert html_to_text("<html><body><p>Tancredus</p><script>x</script></body></html>") == "Tancredus"


def test_sections_are_split():
    sections = split_sections(SAMPLE)
    assert len(sections) == 3
    assert sections[1].title.startswith("Particula VI")


def test_gazetteer_normalizes_latin_forms():
    gazetteer = Gazetteer()
    assert gazetteer.match_token("Tancrede") == "tancred"
    assert gazetteer.match_token("Tancredum") == "tancred"


def test_graph_extracts_weighted_relations():
    graph = build_graph_from_text(SAMPLE)
    labels = {node.label for node in graph.nodes.values()}
    assert "Constance of Sicily" in labels
    assert "Henry VI" in labels
    assert "Tancred of Sicily" in labels
    assert any(edge.relation == "marriage" for edge in graph.edges.values())
    assert any(edge.relation in {"communication", "succession"} for edge in graph.edges.values())
