setup:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
test:
	pytest -q
run-paper:
	python -m src.app.production_pipeline --mode paper --config config.sample.yaml --dry_run
run-shadow:
	python -m src.app.production_pipeline --mode shadow --config config.sample.yaml
run-canary:
	python -m src.app.production_pipeline --mode canary --config config.canary.yaml
run-live:
	python -m src.app.production_pipeline --mode live --config config.live.yaml
