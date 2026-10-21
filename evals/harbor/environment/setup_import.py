from pathlib import Path
import argparse

from evals.harbor.fixtures import import_ledger, raw_inputs, write_json

# The immutable expected baseline is generated separately into the verifier image.
parser = argparse.ArgumentParser(description="Regenerate a synthetic ledger fixture.")
parser.add_argument("--workspace", type=Path, default=Path("/app/ledger"))
parser.add_argument("--expected", type=Path)
args = parser.parse_args()
raw_inputs(Path("/opt/raw-fixtures"))
expected = import_ledger(
    args.workspace,
    Path("/opt/auto-bean-marketplace/plugins/auto-bean"),
    Path("/opt/raw-fixtures"),
)
if args.expected:
    write_json(args.expected, expected)
