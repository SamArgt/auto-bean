#!/bin/bash
set -euo pipefail
printf "stale\n" > /opt/eval-evidence/step-name
python - <<'PY'
import json
from pathlib import Path
root = Path('/app/ledger')
session = json.loads(next((root / '.auto-bean/import-sessions').glob('*.json')).read_text())
source = 'statements/raw/checking.csv'
path = root / next(g['parsed_group'] for g in session['groups'] if source in g['source_files'])
group = json.loads(path.read_text())
doc = next(d for d in group['statements'] if d['source_file'] == source)
row = next(r for r in doc['extracted_records'] if r['record_id'] == 'C-001')
row['review']['rationale'] = 'Updated merchant interpretation requires renewed review.'
path.write_text(json.dumps(group, indent=2, sort_keys=True) + '\n')
PY
