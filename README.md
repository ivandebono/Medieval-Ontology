# ontology

`ontology` builds an interactive relationship network for medieval Sicilian
Latin texts. It currently merges two Latin Library sources:

- Petrus de Ebulo, *Liber ad Honorem Augusti sive de rebus Siculis*  
  <https://www.thelatinlibrary.com/ebulo.html>
- Hugo Falcandus, *Liber de Regno Sicilie*  
  <https://www.thelatinlibrary.com/falcandus.html>

The package extracts people and places, normalizes Latin name variants, detects
relationship cues, and records which document each node, snippet, and source
line came from.

## Setup

This project uses `uv`.

```bash
make sync
```

Run tests:

```bash
make test
```

## Build the Graph

Save the built-in source texts once:

```bash
make texts
```

After that, the Makefile builds from the saved files in `texts/` instead of
fetching the URLs each time:

```bash
uv --cache-dir .uv-cache run ontology build --documents-dir texts --format html --output docs/index.html
uv --cache-dir .uv-cache run ontology build --documents-dir texts --format graphml --output ebulo.graphml
uv --cache-dir .uv-cache run ontology entities --documents-dir texts --limit 30
```

Makefile shortcuts:

```bash
make pages
make graph
make entities
```

To refetch and overwrite the saved source texts:

```bash
make refresh-texts
```

You can still parse one source explicitly:

```bash
uv --cache-dir .uv-cache run ontology build \
  --source https://www.thelatinlibrary.com/ebulo.html \
  --format html \
  --output ebulo.html
```

## Interactive HTML

`make pages` writes `docs/index.html`, a self-contained static graph app. In
the browser:

- click a node to see entity type, mention count, and source documents;
- click a text snippet to expand `+/- n` lines of context;
- change `n` with the context-lines input, default `5`;
- each snippet/context panel shows the source document and section.

This page can be hosted on GitHub Pages.

## Publish with GitHub Pages

After running `make pages`, commit and push `docs/index.html` together with any
code changes that generated it:

```bash
git add docs/index.html src tests README.md
git commit -m "Update medieval ontology graph"
git push
```

Then enable:

```text
Settings -> Pages -> Deploy from a branch -> main -> /docs
```

Your public URL will look like:

```text
https://YOUR-GITHUB-USER.github.io/YOUR-REPO/
```

## Python API

```python
from medieval_ontology.builder import build_graph_from_documents

graph = build_graph_from_documents()
print(graph.top_nodes(10))
graph.write("medieval-sicily.graphml", format="graphml")
```

For a single text:

```python
from medieval_ontology import build_graph_from_text

graph = build_graph_from_text(text, document_id="my_text", document_title="My Text")
```

## Relationships

The extractor combines:

1. a curated gazetteer for people, groups, and places;
2. Latin-aware alias normalization, so forms like `Tancredum`, `Tancrede`, and
   `Tancredus` collapse into one entity;
3. cue-based relationship labels such as `kinship`, `marriage`, `support`,
   `opposition`, `succession`, `communication`, and `rule`;
4. weaker `co-occurrence` edges when entities appear in the same section.

Edge weights are additive. For example, each section-level co-occurrence adds
`0.25`, while stronger sentence-level cues add larger weights.

## Outputs

- `html`: self-contained interactive browser visualization.
- `json`: nodes, edges, snippets, source documents, evidence, and sections.
- `graphml`: import into Gephi, Cytoscape, yEd, or NetworkX.
- `dot`: Graphviz-compatible graph.

## Source Note

Texts are fetched from the Latin Library when you run `make texts` or
`make refresh-texts`. Normal Makefile graph builds read the saved files from
`texts/`. Please consult the Latin Library for its source texts and usage terms.
