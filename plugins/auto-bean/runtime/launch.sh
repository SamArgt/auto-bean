#!/bin/sh
set -eu

runtime_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v uv >/dev/null 2>&1; then
    echo 'uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/.' >&2
    exit 1
fi
export PYTHONDONTWRITEBYTECODE=1
exec uv run --no-project --isolated --python "$(cat "$runtime_dir/.python-version")" python "$runtime_dir/bootstrap.py" "$@"
