from medieval_ontology import build_graph_from_text
from uuid import UUID

from medieval_ontology.gazetteer import Gazetteer
from medieval_ontology.sources import html_to_text
from medieval_ontology.text import split_sections


SAMPLE = """
PETRUS DE EBULO
LIBER AD HONOREM AUGUSTI SIVE DE REBUS SICULIS
Traditur Augusto coniux Constantia magno;
Lucius in nuptu pronuba causa fuit.
Particula VI.: Epistola ad Tancredum
Matheus legit priora verba.
Hanc tibi Matheus mitto Tancrede salutem.
Per me regnabis, per me tibi regna dabuntur.
Ultima verba sequuntur.
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
    tancred_id = gazetteer.match_token("Tancrede")
    assert isinstance(tancred_id, UUID)
    assert gazetteer.get(tancred_id).key == "tancred"
    assert gazetteer.match_token("Tancredum") == tancred_id


def test_graph_extracts_weighted_relations():
    graph = build_graph_from_text(SAMPLE)
    labels = {node.label for node in graph.nodes.values()}
    assert "Constance of Sicily" in labels
    assert "Henry VI" in labels
    assert "Tancred of Sicily" in labels
    tancred = next(node for node in graph.nodes.values() if node.label == "Tancred of Sicily")
    assert any("Tancrede" in snippet or "Tancred" in snippet for snippet in tancred.evidence)
    assert any(edge.relation == "marriage" for edge in graph.edges.values())
    assert any(edge.relation in {"communication", "succession"} for edge in graph.edges.values())


def test_html_titles_do_not_show_break_tags():
    graph = build_graph_from_text(SAMPLE)
    html = graph.to_html()
    assert "Constance of Sicily\\n" in html
    assert "Constance of Sicily\\u003cbr" not in html


def test_node_snippets_carry_clickable_context():
    graph = build_graph_from_text(SAMPLE)
    tancred = next(node for node in graph.nodes.values() if node.label == "Tancred of Sicily")
    snippet = next(item for item in tancred.snippets if "Tancrede" in item.text)
    assert snippet.line_index is not None
    assert graph.source_lines[snippet.line_index]["text"] == snippet.text
    assert graph.source_lines[snippet.line_index - 1]["text"] == "Matheus legit priora verba."
    assert "Per me regnabis" in graph.source_lines[snippet.line_index + 1]["text"]

    html = graph.to_html()
    assert 'id="context-size" type="number" min="0" max="20"' in html
    assert "var contextSize = 5;" in html
    assert "var sourceLines =" in html
    assert "lineIndex" in html
    assert "renderSnippetContext" in html
