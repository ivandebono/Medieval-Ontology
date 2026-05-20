UV := uv --cache-dir .uv-cache

.PHONY: setup sync test build graph html pages entities clean

setup: sync
	$(UV) run python -m ipykernel install --user --name medieval_networks --display-name "MedievalNetworks"

sync:
	$(UV) sync --group dev

test:
	$(UV) run pytest

build:
	$(UV) build

graph:
	$(UV) run ebulo-relations build --format graphml --output ebulo.graphml

html:
	$(UV) run ebulo-relations build --format html --output ebulo.html

pages:
	mkdir -p docs
	$(UV) run ebulo-relations build --format html --output docs/index.html

entities:
	$(UV) run ebulo-relations entities --limit 30

clean:
	rm -rf .venv
	rm -rf .uv-cache .pytest_cache dist build *.egg-info
	jupyter kernelspec uninstall -y medieval_networks 2>/dev/null || true
