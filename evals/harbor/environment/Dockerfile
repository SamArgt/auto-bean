FROM node:22-bookworm-slim@sha256:3ed98443660ff48413b5af19ecefce3b9d50845a901a43420d47cc63a9fddbe9 AS frontend
WORKDIR /build/frontend/import-review
COPY frontend/import-review/package.json frontend/import-review/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/import-review/ ./
COPY plugins/auto-bean/ui/ /build/plugins/auto-bean/ui/
# Rebuild the current checkout, and reject a missing or stale distributed bundle.
RUN cp /build/plugins/auto-bean/ui/bundle.html /tmp/expected-bundle.html && cp /build/plugins/auto-bean/ui/build.json /tmp/expected-build.json && npm run build && cmp /tmp/expected-bundle.html /build/plugins/auto-bean/ui/bundle.html && cmp /tmp/expected-build.json /build/plugins/auto-bean/ui/build.json

FROM node:22-bookworm-slim@sha256:3ed98443660ff48413b5af19ecefce3b9d50845a901a43420d47cc63a9fddbe9 AS base
COPY --from=ghcr.io/astral-sh/uv:0.11.3@sha256:90bbb3c16635e9627f49eec6539f956d70746c409209041800a0280b93152823 /uv /uvx /usr/local/bin/
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates curl ripgrep libglib2.0-0 libgl1 libgomp1 poppler-utils && rm -rf /var/lib/apt/lists/*
ENV PYTHONPATH=/opt
ENV UV_PYTHON_PREFERENCE=only-managed PYTHONDONTWRITEBYTECODE=1 UV_CACHE_DIR=/opt/uv-cache
ENV GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME="Harbor Fixture" GIT_AUTHOR_EMAIL=harbor@example.test GIT_COMMITTER_NAME="Harbor Fixture" GIT_COMMITTER_EMAIL=harbor@example.test
# Build directly from the current checkout, including uncommitted plugin edits.
COPY plugins/auto-bean/runtime /opt/auto-bean-marketplace/plugins/auto-bean/runtime
COPY plugins/auto-bean/assets /opt/auto-bean-marketplace/plugins/auto-bean/assets
COPY evals/harbor/fixtures.py /opt/evals/harbor/fixtures.py
COPY evals/harbor/environment/prefetch.py /tmp/prefetch.py
RUN uv python install 3.13.12
RUN uv run --no-project --python 3.13 --with reportlab==5.0.1 python -c "from pathlib import Path; from evals.harbor.fixtures import raw_inputs; raw_inputs(Path('/opt/raw-fixtures'))"
# Warm dependency downloads without preinitializing the init task's destination.
RUN --mount=type=cache,target=/opt/uv-cache sh /opt/auto-bean-marketplace/plugins/auto-bean/runtime/launch.sh init --workspace /opt/warm-ledger && sh /opt/auto-bean-marketplace/plugins/auto-bean/runtime/launch.sh ensure-runtime --workspace /opt/warm-ledger --extraction && uv run --no-project --python 3.13 /tmp/prefetch.py
COPY plugins/auto-bean /opt/auto-bean-marketplace/plugins/auto-bean
COPY --from=frontend /build/plugins/auto-bean/ui/ /opt/auto-bean-marketplace/plugins/auto-bean/ui/
COPY .agents/plugins/marketplace.json /opt/auto-bean-marketplace/.agents/plugins/marketplace.json
COPY evals/harbor/probe_plugin.py evals/harbor/capture.py /opt/evals/harbor/
COPY evals/harbor/environment/setup_import.py /opt/evals/harbor/setup_import.py
RUN npm install -g @openai/codex@0.163.0 && codex --version
RUN codex plugin marketplace add /opt/auto-bean-marketplace && codex plugin add auto-bean@auto-bean --json && uv run --no-project --python 3.13 /opt/evals/harbor/probe_plugin.py && rm -rf /root/.codex
RUN uv run --no-project --python 3.13 /opt/evals/harbor/capture.py --phase metadata && rm -rf /opt/warm-ledger && chmod -R a-w /opt/auto-bean-marketplace
WORKDIR /app/ledger

FROM base AS init-ledger
# WORKDIR creates an empty destination. Fixtures stay outside this ledger.

FROM base AS import-two-statements
RUN uv run --no-project --python 3.13 --with reportlab==5.0.1 /opt/evals/harbor/setup_import.py

FROM base AS verifier
# Grader code and expected answers exist only in this separate image stage.
RUN sh /opt/auto-bean-marketplace/plugins/auto-bean/runtime/launch.sh init --workspace /opt/verifier-ledger && ln -s /opt/verifier-ledger/.auto-bean/runtime/*/.venv /opt/verifier
ARG HARBOR_TEST_SCRIPT
COPY ${HARBOR_TEST_SCRIPT} /tests/test.sh
COPY evals/harbor/verify.py /opt/evals/harbor/verify.py
RUN uv run --no-project --python 3.13 --with reportlab==5.0.1 /opt/evals/harbor/setup_import.py --workspace /opt/expected-ledger --expected /opt/expected.json && rm -rf /opt/expected-ledger
ENV PYTHONPATH=/opt/auto-bean-marketplace/plugins/auto-bean/runtime:/opt
