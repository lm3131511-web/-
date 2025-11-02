#!/usr/bin/env bash
set -euo pipefail
python -m src.app.production_pipeline --mode live --config config.live.yaml
