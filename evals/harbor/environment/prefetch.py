"""Prefetch and smoke-test the locked Docling pipeline before timing trials."""

import shutil
import subprocess
from pathlib import Path

environments = list(
    Path("/opt/warm-ledger/.auto-bean/runtime").glob("*/.venv/bin/docling")
)
if len(environments) != 1:
    raise RuntimeError("Expected exactly one extraction runtime")
binary = environments[0].parent
subprocess.run([str(binary / "docling-tools"), "models", "download"], check=True)
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
# Keep model cache and uv downloads, but never leak extracted answers into trials.
shutil.rmtree("/opt/extraction-smoke")
