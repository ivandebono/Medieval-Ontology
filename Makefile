UV := uv --cache-dir .uv-cache
TEXTS_DIR := texts

.PHONY: setup sync test build texts refresh-texts graph html pages entities clean

setup: sync
	$(UV) run python -m ipykernel install --user --name medieval_networks --display-name "MedievalNetworks"

sync:
	$(UV) sync --group dev

test:
	$(UV) run pytest

build:
	$(UV) build

texts:
	$(UV) run ontology cache-sources --output $(TEXTS_DIR)

refresh-texts:
	$(UV) run ontology cache-sources --output $(TEXTS_DIR) --refresh

graph: texts
	$(UV) run ontology build --documents-dir $(TEXTS_DIR) --format graphml --output ebulo.graphml

html: texts
	$(UV) run ontology build --documents-dir $(TEXTS_DIR) --format html --output ebulo.html

pages: texts
	mkdir -p docs
	$(UV) run ontology build --documents-dir $(TEXTS_DIR) --format html --output docs/index.html

entities: texts
	$(UV) run ontology entities --documents-dir $(TEXTS_DIR) --limit 30

clean:
	rm -rf .venv
	rm -rf .uv-cache .pytest_cache dist build *.egg-info
	jupyter kernelspec uninstall -y medieval_networks 2>/dev/null || true
