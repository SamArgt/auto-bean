#!/bin/bash
set -euo pipefail
printf "stale\n" > /opt/eval-evidence/step-name
python - <<'PY'
import json
from pathlib import Path
path = Path('/app/ledger/statements/parsed/checking.json')
doc = json.loads(path.read_text())
row = next(r for r in doc['extracted_records'] if r['record_id'] == 'C-001')
row['review']['rationale'] = 'Updated merchant interpretation requires renewed review.'
path.write_text(json.dumps(doc, indent=2, sort_keys=True) + '\n')
PY
