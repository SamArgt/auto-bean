#!/bin/bash
set -euo pipefail
/opt/verifier/bin/python /opt/evals/harbor/verify.py correct --ledger /app/ledger --plugin /opt/auto-bean-marketplace/plugins/auto-bean --expected /opt/expected.json
