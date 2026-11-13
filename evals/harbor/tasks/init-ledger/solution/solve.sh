#!/bin/bash
set -euo pipefail
sh /opt/auto-bean-marketplace/plugins/auto-bean/runtime/launch.sh init --workspace /app/ledger
uv run --no-project /opt/evals/harbor/capture.py --phase init
