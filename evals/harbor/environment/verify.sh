#!/bin/bash
set -euo pipefail
# The task's verifier Compose file supplies the phase. Agent artifacts do not.
exec /opt/verifier/bin/python /opt/evals/harbor/verify.py "${AUTO_BEAN_EVAL_PHASE:?Verifier phase is required}" \
  --ledger /app/ledger \
  --plugin /opt/auto-bean-marketplace/plugins/auto-bean \
  --expected /opt/expected.json
