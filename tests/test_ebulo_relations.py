import json
from uuid import UUID

from medieval_ontology import build_graph_from_text
from medieval_ontology.analysis import write_graphml_structure_insights
from medieval_ontology.builder import build_graph_from_documents
from medieval_ontology.gazetteer import Gazetteer
from medieval_ontology.sources import Document, cached_documents, save_documents
from medieval_ontology.graph import mention_label
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
    assert gazetteer.get(tancred_id).wikipedia_url == "https://en.wikipedia.org/wiki/Tancred,_King_of_Sicily"
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
    assert 'id="context-size" type="number" min="0" max="250" step="5"' in html
    assert "var contextSize = 40;" in html
    assert "wikipediaUrl" in html
    assert "external-link" in html
    assert 'target="_blank" rel="noopener noreferrer"' in html
    assert "var sourceDocuments =" in html
    assert "Context words" in html
    assert "function trailingWords" in html
    assert "lineIndex" in html
    assert "renderSnippetContext" in html


def test_node_count_matches_visible_snippets():
    graph = build_graph_from_text(SAMPLE)
    for node in graph.nodes.values():
        assert node.count == len(node.snippets)


def test_mention_label_pluralizes():
    assert mention_label(1) == "mention"
    assert mention_label(0) == "mentions"
    assert mention_label(2) == "mentions"

    html = build_graph_from_text(SAMPLE).to_html()
    assert 'function mentionLabel(count)' in html
    assert 'mentionLabel(node.mentions || 0)' in html


def test_merged_documents_track_node_provenance(tmp_path):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("Particula I\nTancredus Matheus venit.\n", encoding="utf-8")
    second.write_text("Particula I\nTancrede Matheus loquitur.\n", encoding="utf-8")

    graph = build_graph_from_documents(
        (
            Document("doc_a", "First Book", str(first)),
            Document("doc_b", "Second Book", str(second)),
        )
    )
    tancred = next(node for node in graph.nodes.values() if node.label == "Tancred of Sicily")
    assert tancred.documents == {"doc_a", "doc_b"}
    assert {snippet.document_id for snippet in tancred.snippets} == {"doc_a", "doc_b"}
    assert graph.source_documents["doc_a"].lines == [{"text": "Tancredus Matheus venit.", "section": "Particula I"}]
    assert graph.source_documents["doc_b"].lines == [{"text": "Tancrede Matheus loquitur.", "section": "Particula I"}]
    assert {snippet.line_index for snippet in tancred.snippets} == {0}

    payload = json.loads(graph.to_json())
    assert payload["documents"] == [
        {
            "id": "doc_a",
            "title": "First Book",
            "lines": [{"text": "Tancredus Matheus venit.", "section": "Particula I"}],
        },
        {
            "id": "doc_b",
            "title": "Second Book",
            "lines": [{"text": "Tancrede Matheus loquitur.", "section": "Particula I"}],
        },
    ]

    html = graph.to_html()
    assert "First Book" in html
    assert "Second Book" in html
    assert '"documentId": "doc_a"' in html
    assert "var sourceDocuments =" in html


def test_sources_can_be_saved_and_reused_from_disk(tmp_path):
    source = tmp_path / "source.html"
    source.write_text("<html><body><p>Tancredus</p><p>Matheus</p></body></html>", encoding="utf-8")

    output_dir = tmp_path / "texts"
    document = Document("sample", "Sample", str(source))
    paths = save_documents(output_dir, documents=(document,))

    assert paths == [output_dir / "sample.txt"]
    assert paths[0].read_text(encoding="utf-8") == "Tancredus\nMatheus"
    assert cached_documents(output_dir, documents=(document,)) == (
        Document("sample", "Sample", str(output_dir / "sample.txt")),
    )

    source.write_text("<html><body><p>Changed</p></body></html>", encoding="utf-8")
    save_documents(output_dir, documents=(document,))
    assert paths[0].read_text(encoding="utf-8") == "Tancredus\nMatheus"

    save_documents(output_dir, documents=(document,), refresh=True)
    assert paths[0].read_text(encoding="utf-8") == "Changed"


def test_graphml_analysis_writes_structural_insights(tmp_path):
    graph = build_graph_from_text(SAMPLE)
    graphml = tmp_path / "sample.graphml"
    output = tmp_path / "insights.json"
    graph.write(graphml, format="graphml")

    write_graphml_structure_insights(graphml, output, top_n=3)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["nodeCount"] == len(graph.nodes)
    assert payload["summary"]["edgeCount"] > 0
    assert payload["topDegreeCentrality"]
    assert len(payload["topDegreeCentrality"]) <= 3
    assert "co-occurrence" in {item["relation"] for item in payload["relations"]}
