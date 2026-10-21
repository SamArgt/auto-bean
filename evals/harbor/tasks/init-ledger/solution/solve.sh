#!/bin/bash
set -euo pipefail
sh /opt/auto-bean-marketplace/plugins/auto-bean/runtime/launch.sh init --workspace /app/ledger
uv run --no-project --python 3.13 /opt/evals/harbor/capture.py --phase initial
