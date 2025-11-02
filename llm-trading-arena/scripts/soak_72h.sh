#!/usr/bin/env bash
set -euo pipefail
end=$((SECONDS + 72 * 3600))
while [ $SECONDS -lt $end ]; do
  python -m src.app.production_pipeline --mode shadow --config config.canary.yaml
  sleep 60
done
