#!/bin/bash
set -euo pipefail
phase=$(cat /opt/eval-evidence/step-name)
sh /opt/auto-bean-marketplace/plugins/auto-bean/runtime/launch.sh run --workspace /app/ledger python -c 'import runpy, sys; sys.path.insert(0, "/opt"); runpy.run_path(sys.argv.pop(1), run_name="__main__")' /solution/reference.py "$phase"
