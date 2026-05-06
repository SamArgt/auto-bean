#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required to install auto-bean workspace dependencies." >&2
  echo "Install uv, then rerun ./scripts/install-dependencies.sh." >&2
  echo "See: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

uv venv .venv
uv pip install --python ./.venv/bin/python beancount fava docling

echo "Workspace dependencies installed in ./.venv"
