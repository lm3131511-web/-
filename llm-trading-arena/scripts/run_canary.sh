#!/usr/bin/env bash
set -euo pipefail
python -m src.app.production_pipeline --mode canary --config config.canary.yaml
