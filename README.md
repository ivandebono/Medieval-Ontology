# ontology

`ontology` builds a relationship network graph from Petrus de Ebulo's
*Liber ad honorem Augusti sive de rebus Siculis*, using the Latin Library text:

<https://www.thelatinlibrary.com/ebulo.html>

It is designed for exploratory historical work: it extracts candidate people
and places, normalizes common Latin name variants, detects relationship cues,
and exports a weighted graph.

## Install

```bash
python -m pip install -e ".[dev]"
```

## Quick Start

```bash
ontology build --format json --output ebulo.graph.json
ontology build --format graphml --output ebulo.graphml
ontology build --format html --output ebulo.html
ontology entities --limit 30
```

## Shareable Web Page

Generate a static page for GitHub Pages or any static host:

```bash
make pages
```

This writes `docs/index.html`. If the repository is on GitHub, enable
**Settings -> Pages -> Deploy from a branch -> main / docs**. The public URL
will look like:

```text
https://YOUR-GITHUB-USER.github.io/YOUR-REPO/
```

The default source is the Latin Library URL. You can also use a saved file:

```bash
ontology build --source ./ebulo.html --format dot --output ebulo.dot
```

## Python API

```python
from medieval_ontology import build_graph_from_source

graph = build_graph_from_source("https://www.thelatinlibrary.com/ebulo.html")
print(graph.top_nodes(10))
graph.write("ebulo.graphml", format="graphml")
```

## What Counts as a Relationship?

The package combines three layers:

1. A curated gazetteer for major people and places in the text.
2. Latin-aware alias normalization, so forms like `Tancredum`, `Tancrede`, and
   `Tancredus` can collapse into one node.
3. Pattern cues for relations such as kinship, marriage, support, opposition,
   succession, writing/sending, rulership, and section-level co-mention.

This is deliberately transparent rather than magical. The output edges include
evidence snippets and section labels so scholars can inspect the basis of each
connection.

## Outputs

- `json`: nodes, edges, weights, labels, evidence, and sections.
- `graphml`: import into Gephi, Cytoscape, yEd, or NetworkX.
- `dot`: Graphviz-compatible graph.
- `html`: a self-contained SVG network overview.

## Source Note

The text is fetched from the Latin Library at runtime unless you pass a local
file. Please consult the Latin Library for its source text and usage terms.
