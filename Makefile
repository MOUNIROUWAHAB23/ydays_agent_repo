.PHONY: install ingest run cli test lint docker-up docker-ingest

install:
	pip install -r requirements-dev.txt

ingest:
	PYTHONPATH=src python scripts/ingest.py

run:
	PYTHONPATH=src streamlit run src/copilote/ui.py

cli:
	PYTHONPATH=src python -m copilote.cli

test:
	pytest --cov=src/copilote --cov-report=term-missing

lint:
	ruff check src tests

docker-up:
	docker compose up --build

docker-ingest:
	docker compose --profile tools run --rm ingest
