#!/usr/bin/env bash
set -euo pipefail

cat <<'INSTRUCTIONS'
Codex key rotation checklist:
  1. Request new provider credentials from the corresponding secret owners.
  2. Store the secrets in the vault/sops backend. Never commit them to git.
  3. Update the vault references used by the deployment manifests.
  4. Redeploy Codex with the updated secret versions.
  5. Validate access via `scripts/check_config.py` and the `/health` endpoint.
INSTRUCTIONS
