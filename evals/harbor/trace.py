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
    agent_id: str | None = None


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

# Accept only the documented helper body. Never infer execution from arbitrary
# function source, and never execute submitted shell code during verification.
LAUNCHER_FUNCTION = re.compile(
    r'auto_bean\(\)\s*\{\s*if\s+\[\s+"\$1"\s+=\s+validate\s*\];\s*then\s+'
    r'shift\s*;?\s*sh\s+"\$AUTO_BEAN_PLUGIN/runtime/launch.sh"\s+validate\s+"\$@"\s*;?\s*'
    r'else\s+sh\s+"\$AUTO_BEAN_PLUGIN/runtime/launch.sh"\s+run\s+--workspace\s+'
    r'"\$AUTO_BEAN_WORKSPACE"\s+"\$@"\s*;?\s*fi\s*;?\s*\}'
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
    function_lines = ""
    helper: bool | None = None

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
        if function_lines or re.search(r"\w+\s*\(\s*\)\s*\{", line):
            function_lines += line + "\n"
            if function_lines.count("{") > function_lines.count("}"):
                continue
            match = LAUNCHER_FUNCTION.search(function_lines)
            prefix = function_lines[: match.start()] if match else ""
            # A definition must be a top-level command, not quoted data or a
            # conditional branch. Only literal assignments may precede it.
            if match and re.fullmatch(
                r"(?:\s*(?:export\s+)?AUTO_BEAN_(?:PLUGIN|WORKSPACE)=[^;\n]+[;\n])*\s*",
                prefix,
            ):
                helper = True
                line = prefix + function_lines[match.end() :].lstrip("; \n")
                line = line.strip().replace("\n", "; ")
            else:
                helper = False
                function_lines = ""
                continue
            function_lines = ""
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
        separators: list[str] = []
        for token in tokens:
            if token in {";", "&&"}:
                separators.append(token)
                groups.append([])
            else:
                groups[-1].append(token)
        line_result: list[tuple[tuple[str, ...], str]] = []
        conditional = False
        for index, group in enumerate(groups):
            if index and separators[index - 1] == ";":
                line_result = []
                conditional = False
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
            assignments = []
            while group and re.match(r"^[A-Za-z_][A-Za-z_0-9]*=", group[0]):
                assignments.append(group.pop(0).split("=", 1))
            prefixed = bool(assignments and group)
            if prefixed and any(
                key not in {"AUTO_BEAN_PLUGIN", "AUTO_BEAN_WORKSPACE"}
                or "$" in value
                or "`" in value
                for key, value in assignments
            ):
                conditional = True
                continue
            # Shell expansion happens before a command-prefix environment is
            # applied. Credit literal launcher commands without leaking these
            # assignments into subsequent commands or resolving helper bodies.
            for key, value in [] if prefixed else assignments:
                if conditional:
                    variables.pop(key, None)
                else:
                    variables[key] = re.sub(r"\$(?:\{(\w+)\}|(\w+))", substitute, value)
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
            conditional = True
            if expanded[0] == "cd" and len(expanded) == 2:
                if (
                    index < len(separators)
                    and separators[index] == "&&"
                    and ";" not in separators[index:]
                ):
                    cwd = absolute(expanded[1], cwd)
                else:
                    cwd = "/__unproven_cwd__"
                continue
            # Redirected data is not a read. Avoid crediting hidden output too.
            if any(t in {">", ">>", "<", "<<"} for t in expanded):
                continue
            if expanded[0] == "auto_bean" and helper is not None:
                if prefixed or not helper or not variables.get("AUTO_BEAN_PLUGIN"):
                    continue
                launcher = variables["AUTO_BEAN_PLUGIN"] + "/runtime/launch.sh"
                if expanded[1:2] == ["validate"]:
                    expanded = ["sh", launcher, *expanded[1:]]
                else:
                    expanded = [
                        "sh",
                        launcher,
                        "run",
                        "--workspace",
                        variables.get("AUTO_BEAN_WORKSPACE", ""),
                        *expanded[1:],
                    ]
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
    # Plain timeout propagates the child's exit status. Options such as
    # --preserve-status, arbitrary wrappers and invalid/zero durations do not count.
    if argv[0] in {"timeout", "/usr/bin/timeout"}:
        if len(argv) < 3 or not re.fullmatch(r"[1-9]\d*(?:\.\d+)?[smhd]?", argv[1]):
            return False
        argv = argv[2:]
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
                subagent = source.get("subagent", {})
                spawn = subagent.get("thread_spawn", subagent.get("spawn", {}))
                parent = spawn.get("parent_thread_id")
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
                        str(meta.get("id", meta.get("session_id")))
                        if meta.get("id", meta.get("session_id")) != root_id
                        else None,
                    )
                )
    return result


def grade_trace(
    logs: Path,
    phase: str,
    stage_groups: dict[str, list[dict[str, Any]]] | None = None,
    parsed_paths: list[str] | None = None,
) -> dict[str, Any]:
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
    assignments: list[set[str]] = []
    for stage, groups in (stage_groups or {}).items():
        for group in groups:
            candidates = {
                c.agent_id
                for c in commands
                if c.agent_id and plugin_read(c, f"skills/auto-bean-{stage}/SKILL.md")
            }
            candidates = {
                agent
                for agent in candidates
                if all(
                    any(
                        c.agent_id == agent
                        and (
                            workspace_read(c, path)
                            or (stage == "process" and operation(c, "docling", path))
                        )
                        for c in current
                    )
                    for path in group["paths"]
                )
            }
            check(
                f"subagent:{stage}:{group['group_id']}",
                [c for c in current if c.agent_id in candidates],
            )
            assignments.append(candidates)

    def distinct_workers(pending: list[set[str]], used: set[str]) -> bool:
        if not pending:
            return True
        return any(
            distinct_workers(pending[1:], used | {agent}) for agent in pending[0] - used
        )

    if assignments:
        check(
            "subagents:separate-group-stage-workers",
            [c for c in current if c.agent_id]
            if distinct_workers(sorted(assignments, key=len), set())
            else [],
        )
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
            "schemas/parsed-group.schema.json",
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
        files += (
            parsed_paths
            if parsed_paths is not None
            else ["statements/parsed/january.json"]
        )
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
