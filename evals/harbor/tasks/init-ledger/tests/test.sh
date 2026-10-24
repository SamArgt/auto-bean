#!/bin/bash
set -euo pipefail
/opt/verifier/bin/python /opt/evals/harbor/verify.py init --ledger /app/ledger --plugin /opt/auto-bean-marketplace/plugins/auto-bean
