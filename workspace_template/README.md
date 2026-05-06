# auto-bean workspace

This is a Git-backed Beancount ledger workspace operated through the installed auto-bean Codex skills. It contains your ledger, statements, parsed evidence, governed memory, and local runtime state.

## Quick Start

### Requirements

- macOS
- Python `>=3.13,<3.14`
- [`uv`](https://docs.astral.sh/uv/)
- Git
- Codex as the coding agent for this workspace

### Install Dependencies

Fresh `auto-bean init` workspaces are installed before the initial commit. After cloning this workspace from a remote GitHub repository, recreate the local runtime:

```bash
./scripts/install-dependencies.sh
```

This creates `./.venv` and installs Beancount, Fava, and Docling into the workspace-local environment.

### Validate The Ledger

```bash
./scripts/validate-ledger.sh
```

### Open In Fava

```bash
./scripts/open-fava.sh
```

### Import Statements

Put bank, card, or account statements in:

```text
statements/raw/
```

Then ask Codex from inside this workspace:

```text
$auto-bean-import
```

The import workflow parses supported raw files into `statements/parsed/`, proposes ledger updates, validates the ledger, surfaces review details, records eligible reusable memory, and stops for user approval before finalized ledger history is committed.
