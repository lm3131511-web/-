#!/usr/bin/env bash
set -euo pipefail
python -m src.app.production_pipeline --mode shadow --config config.sample.yaml
