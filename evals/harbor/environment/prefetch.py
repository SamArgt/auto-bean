"""Cache only the models used by the locked default CSV/PDF pipeline."""

import shutil
import subprocess
from pathlib import Path

environments = list(
    Path("/opt/warm-ledger/.auto-bean/runtime").glob("*/.venv/bin/docling")
)
if len(environments) != 1:
    raise RuntimeError("Expected exactly one extraction runtime")
binary = environments[0].parent
# Running the real conversions fetches their required models. The broad models
# download command also fetches unused code/formula and figure classifiers and
# duplicates artifacts in a second model cache.
for path in sorted(Path("/opt/raw-fixtures").iterdir()):
    subprocess.run(
        [
            str(binary / "docling"),
            str(path),
            "--to",
            "json",
            "--output",
            "/opt/extraction-smoke",
        ],
        check=True,
        timeout=120,
    )
# Keep the required model cache, but never leak extracted answers into trials.
shutil.rmtree("/opt/extraction-smoke")
