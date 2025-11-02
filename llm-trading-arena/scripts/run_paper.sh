#!/usr/bin/env bash
set -euo pipefail
python -m src.app.production_pipeline --mode paper --config config.sample.yaml --dry_run
