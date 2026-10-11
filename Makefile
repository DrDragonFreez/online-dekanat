.PHONY: install dev batch-open test clean
install:
	python -m pip install -r requirements.txt
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
batch-open:
	python scripts/run_open.py
	python scripts/evaluate.py \
		--reference data/reference_results.json \
		--predictions results/results_open.json
test:
	pytest -q
clean:
	rm -f data/uploads/*
	rm -f results/*.json