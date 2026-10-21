#!/bin/bash
set -euo pipefail
phase=review
if test -f /opt/eval-evidence/review.json; then phase=approve; fi
sh /opt/auto-bean-marketplace/plugins/auto-bean/runtime/launch.sh run --workspace /app/ledger python /solution/reference.py "$phase"
