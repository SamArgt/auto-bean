"""Grade observed plugin use from native Codex command-completion events.

This is trace evidence, not a system-call audit. Never execute submitted code.
Only the pinned CLI's completed command events count, not prose or tool output
that merely mentions a command. Unknown shell constructs fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
import fnmatch
import json
import re
import shlex


@dataclass(frozen=True)
class Command:
    reference: str
    current: bool
    argv: tuple[str, ...]
    cwd: str


SKILLS = {
    "init": ("init",),
    "review": ("import", "process", "query", "categorize"),
    "needs-input": ("import", "process", "query", "categorize"),
    "correct": ("import", "query", "categorize"),
    "approve": ("import", "write", "query", "prices", "memory"),
    "stale": ("import",),
}
PLUGIN_ROOTS = (
    "/tmp/codex-home/plugins/cache/auto-bean/auto-bean/*",
    "/opt/auto-bean-marketplace/plugins/auto-bean",
)


def expand_braces(value: str) -> list[str]:
    match = re.search(r"\{([^{}]+,[^{}]+)\}", value)
    if not match:
        return [value]
    return [
        expanded
        for part in match[1].split(",")
        for expanded in expand_braces(
            value[: match.start()] + part + value[match.end() :]
        )
    ]


def shell_commands(script: str, cwd: str) -> list[tuple[tuple[str, ...], str]]:
    """Recognize literal shell commands; skip scripts, function bodies and data.

    Assignments resolve the documented launcher variables. Shell source files and
    Python/JS programs are opaque; their text is never searched for claimed actions.
    """
    variables: dict[str, str] = {}
    result: list[tuple[tuple[str, ...], str]] = []
    heredoc: str | None = None
    depth = 0

    def substitute(match: re.Match[str]) -> str:
        return variables.get(match[1] or match[2], match[0])

    for line in script.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        result = []
        if heredoc:
            if line.strip() == heredoc:
                heredoc = None
            continue
        here = re.search(r"<<-?\s*['\"]?(\w+)", line)
        if here:
            heredoc = here[1]
            continue
        if depth:
            depth += line.count("{") - line.count("}")
            continue
        if re.search(r"\w+\s*\(\s*\)\s*\{", line):
            depth = line.count("{") - line.count("}")
            continue
        try:
            lexer = shlex.shlex(line, posix=False, punctuation_chars=";&|<>()")
            lexer.whitespace_split = True
            tokens = list(lexer)
        except ValueError:
            continue
        # Conditional branches, pipelines, subshells and substitutions need a
        # shell AST. Do not guess whether a mentioned command actually ran.
        if any(
            t in {"||", "|", "&", "(", ")", "if", "then", "for", "while"}
            for t in tokens
        ):
            continue
        groups: list[list[str]] = [[]]
        for token in tokens:
            if token == ";":
                # A later command can mask an earlier failure. Only the final
                # AND-list in a semicolon sequence has a proven zero status.
                groups = [[]]
            elif token == "&&":
                groups.append([])
            else:
                groups[-1].append(token)
        line_result = []
        for group in groups:
            if not group:
                continue
            # Preserve quoted separators until after command boundaries are set.
            # Quoted variable references are deliberately left unresolved here.
            literal_variables = {
                token[1:-1]
                for token in group
                if token.startswith("'") and token.endswith("'")
            }
            try:
                group = shlex.split(" ".join(group))
            except ValueError:
                continue
            if group[0] == "export":
                group = group[1:]
            while group and re.match(r"^[A-Za-z_][A-Za-z_0-9]*=", group[0]):
                key, value = group.pop(0).split("=", 1)
                variables[key] = value
            expanded = [
                value
                if value in literal_variables
                else re.sub(
                    r"\$(?:\{(\w+)\}|(\w+))",
                    substitute,
                    value,
                )
                for value in group
            ]
            if not expanded or any("$(" in t or "`" in t for t in expanded):
                continue
            if expanded[0] == "cd" and len(expanded) == 2:
                cwd = absolute(expanded[1], cwd)
                continue
            # Redirected data is not a read. Avoid crediting hidden output too.
            if any(t in {">", ">>", "<", "<<"} for t in expanded):
                continue
            line_result.append((tuple(expanded), cwd))
        if line_result:
            # Newlines also mask earlier exit statuses. Assignments above still
            # resolve variables, but only the final executable line is credited.
            result = line_result
    return result


def absolute(path: str, cwd: str) -> str:
    import posixpath

    return posixpath.normpath(path if path.startswith("/") else f"{cwd}/{path}")


def path_matches(value: str, pattern: str) -> bool:
    """Shell stars match one path component, never an arbitrary subtree."""
    values, patterns = value.split("/"), pattern.split("/")
    return len(values) == len(patterns) and all(
        fnmatch.fnmatchcase(v, p) for v, p in zip(values, patterns)
    )


def read_paths(command: Command) -> list[str]:
    """Only content-reading tools count. Listing and output text do not count."""
    argv = command.argv
    name = PurePosixPath(argv[0]).name
    if name not in {"cat", "head", "tail", "sed", "jq", "rg", "grep"}:
        return []
    if name in {"rg", "grep"} and any(
        x in argv
        for x in (
            "--files",
            "-l",
            "-L",
            "-q",
            "-c",
            "--quiet",
            "--count",
            "--files-with-matches",
            "--files-without-match",
        )
    ):
        return []
    # Skip filters and option values. Remaining path-like operands are bounded
    # below by exact workspace paths or installed plugin resource paths.
    operands = list(argv[1:])
    if name in {"sed", "jq", "rg", "grep"}:
        while operands and operands[0].startswith("-"):
            option = operands.pop(0)
            if option in {"-e", "--arg", "--argjson", "-f"}:
                return []
        if operands:
            operands.pop(0)
    return [
        absolute(path, command.cwd)
        for value in operands
        if not value.startswith("-")
        for path in expand_braces(value)
    ]


def plugin_read(command: Command, relative: str) -> bool:
    for path in read_paths(command):
        for root in PLUGIN_ROOTS:
            # The cache version is the only wildcard in the trusted root.
            prefix, suffix = (
                path.rsplit("/skills/", 1) if "/skills/" in path else ("", "")
            )
            if relative.startswith("skills/") and path_matches(prefix, root):
                if path_matches(relative.removeprefix("skills/"), suffix):
                    return True
            if "/references/" in path and relative.startswith("references/"):
                prefix, suffix = path.split("/references/", 1)
                if path_matches(prefix, root) and path_matches(
                    relative.removeprefix("references/"), suffix
                ):
                    return True
    return False


def workspace_read(command: Command, relative: str) -> bool:
    expected = f"/app/ledger/{relative}"
    return any(path_matches(expected, path) for path in read_paths(command))


def operation(command: Command, name: str, *args: str) -> bool:
    argv = command.argv
    if argv[0] == "auto_bean":
        tail = argv[1:]
    elif argv[0] in {"sh", "bash"} and len(argv) > 2:
        launcher = argv[1]
        if not launcher.endswith("/runtime/launch.sh") or not any(
            path_matches(launcher.removesuffix("/runtime/launch.sh"), root)
            for root in PLUGIN_ROOTS
        ):
            return False
        tail = argv[2:]
        if tail[:1] == ("run",):
            if tail[1:3] != ("--workspace", "/app/ledger"):
                return False
            tail = tail[3:]
    else:
        return False
    if not tail or tail[0] != name:
        return False
    if any(arg in tail for arg in ("--help", "-h", "--version")):
        return False
    if name in {"init", "validate", "ensure-runtime"}:
        if not any(
            tail[i : i + 2] == ("--workspace", "/app/ledger") for i in range(len(tail))
        ):
            return False
    if "--session" in args:
        if "--session" not in tail:
            return False
        index = tail.index("--session")
        if index + 1 == len(tail) or tail[index + 1].startswith("-"):
            return False
    if "--stage" in args:
        stage = args[args.index("--stage") + 1]
        if not any(tail[i : i + 2] == ("--stage", stage) for i in range(len(tail))):
            return False
    for arg in args:
        if arg in {
            "ledger.beancount",
            "statements/raw/checking.csv",
            "statements/raw/savings.pdf",
        }:
            if not any(
                absolute(value, command.cwd) == f"/app/ledger/{arg}"
                for value in tail[1:]
            ):
                return False
        elif arg not in tail[1:]:
            return False
    return True


def load_commands(logs: Path) -> list[Command]:
    files = sorted((logs / "sessions").rglob("*.jsonl"))
    if not files:
        raise ValueError("Missing native Codex session trace")
    sessions: list[tuple[Path, list[dict[str, Any]], dict[str, Any]]] = []
    for path in files:
        events = [
            json.loads(line) for line in path.read_text().splitlines() if line.strip()
        ]
        meta = next(e["payload"] for e in events if e.get("type") == "session_meta")
        sessions.append((path, events, meta))
    roots = [s for s in sessions if s[2].get("source") == "exec"]
    if len(roots) != 1:
        raise ValueError("Expected one root Codex exec session")
    _, root_events, root_meta = roots[0]
    starts = [
        e for e in root_events if e.get("payload", {}).get("type") == "task_started"
    ]
    if not starts:
        raise ValueError("Missing native task_started boundary")
    latest = starts[-1]
    boundary = latest["timestamp"]
    root_id = root_meta.get("id", root_meta.get("session_id"))
    allowed = {root_id}
    # Only descendant sessions may supply delegated skill/command evidence.
    for _ in sessions:
        for _, _, meta in sessions:
            source = meta.get("source", {})
            if isinstance(source, dict):
                parent = (
                    source.get("subagent", {}).get("spawn", {}).get("parent_thread_id")
                )
                if parent in allowed:
                    allowed.add(meta.get("id", meta.get("session_id")))
    result = []
    for path, events, meta in sessions:
        if meta.get("id", meta.get("session_id")) not in allowed:
            continue
        for line_number, event in enumerate(events, 1):
            payload = event.get("payload", {})
            if (
                event.get("type") != "event_msg"
                or payload.get("type") != "item_completed"
            ):
                continue
            item = payload.get("item", {})
            if (
                item.get("type") != "CommandExecution"
                or item.get("status") != "completed"
                or item.get("exit_code") != 0
            ):
                continue
            argv = item.get("command", [])
            if (
                len(argv) != 3
                or PurePosixPath(argv[0]).name not in {"bash", "sh", "zsh"}
                or argv[1] not in {"-lc", "-c"}
            ):
                continue
            cwd = item.get("cwd", "/app/ledger").removeprefix("file://")
            for command, directory in shell_commands(argv[2], cwd):
                result.append(
                    Command(
                        f"{path.relative_to(logs)}:{line_number}:{item.get('id', '')}",
                        event["timestamp"] >= boundary,
                        command,
                        directory,
                    )
                )
    return result


def grade_trace(logs: Path, phase: str) -> dict[str, Any]:
    report: dict[str, Any] = {"phase": phase, "passed": False, "checks": []}
    try:
        commands = load_commands(logs)
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        StopIteration,
        OSError,
    ) as exc:
        report["failure"] = str(exc) or "Malformed native trace"
        return report

    def check(label: str, matches: list[Command]) -> None:
        report["checks"].append(
            {
                "requirement": label,
                "passed": bool(matches),
                "evidence": list(dict.fromkeys(c.reference for c in matches)),
            }
        )

    current = [c for c in commands if c.current]
    for skill in SKILLS[phase]:
        check(
            f"skill:{skill}",
            [
                c
                for c in commands
                if plugin_read(c, f"skills/auto-bean-{skill}/SKILL.md")
            ],
        )
    references = ["common.md"]
    if phase != "init":
        references += [
            "import-review.md",
            "schemas/parsed-v2.schema.json",
            "schemas/session.schema.json",
            "schemas/status.schema.json",
        ]
    if phase == "approve":
        references += ["schemas/memory.schema.json"]
    for reference in references:
        check(
            f"reference:{reference}",
            [c for c in commands if plugin_read(c, f"references/{reference}")],
        )
    files = ["ledger.beancount", ".auto-bean/workspace.json"]
    if phase != "init":
        files += [
            "statements/import-status.yml",
            ".auto-bean/memory/MEMORY.md",
            "beancount/accounts.beancount",
        ]
    if phase in {"correct", "approve", "stale"}:
        files += ["statements/parsed/checking.json", "statements/parsed/savings.json"]
    if phase == "approve":
        files += [
            ".auto-bean/memory/account_mappings.json",
            ".auto-bean/memory/category_mappings.json",
        ]
    for file in files:
        # Common guidance says to load workspace context once per session.
        # Mutable review inputs and learning targets must be read in this turn.
        scope = (
            commands
            if file
            in {
                ".auto-bean/workspace.json",
                ".auto-bean/memory/MEMORY.md",
                "beancount/accounts.beancount",
            }
            else current
        )
        check(f"read:{file}", [c for c in scope if workspace_read(c, file)])
    check(
        "command:git-status",
        [
            c
            for c in current
            if c.cwd == "/app/ledger" and c.argv[:2] == ("git", "status")
        ],
    )
    required: list[tuple[str, ...]] = []
    if phase == "init":
        required = [("init",)]
    elif phase in {"review", "needs-input"}:
        required = [
            ("ensure-runtime", "--extraction"),
            ("docling", "statements/raw/checking.csv"),
            ("docling", "statements/raw/savings.pdf"),
            ("bean-query", "ledger.beancount"),
        ]
    elif phase == "correct":
        required = [("bean-query", "ledger.beancount")]
    if phase in {"review", "correct"}:
        required += [("validate", "--session", "--stage", "review")]
    if phase == "approve":
        required = [("validate", "--session", "--stage", "written")]
    for spec in required:
        check(
            "command:" + " ".join(spec),
            [c for c in current if operation(c, spec[0], *spec[1:])],
        )
    report["passed"] = all(c["passed"] for c in report["checks"])
    return report
