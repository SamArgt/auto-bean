"""Require a stable plugin version greater than the pull request base version."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "plugins/auto-bean/plugin.json"


def version_tuple(value: object) -> tuple[int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(
        r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value
    ):
        raise ValueError(f"Expected a stable major.minor.patch version, got {value!r}.")
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def check_version_increment(base_ref: str, root: Path = ROOT) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", base_ref):
        raise ValueError("The base reference must be a full commit SHA.")
    base = json.loads(
        subprocess.run(
            ["git", "show", f"{base_ref}:{MANIFEST}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    ).get("version")
    current = json.loads((root / MANIFEST).read_text()).get("version")
    if version_tuple(current) <= version_tuple(base):
        raise ValueError(
            f"Plugin version must increase above base version {base}; found {current}."
        )
    return f"Plugin version increased: {base} -> {current}."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True)
    args = parser.parse_args()
    try:
        print(check_version_increment(args.base_ref))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Version check failed: {error}\n")


if __name__ == "__main__":
    main()
