"""Grade observed plugin use from native Codex command-completion events.

This is trace evidence, not a system-call audit. Never execute submitted code.
Only the pinned CLI's completed command events count, not prose or tool output
that merely mentions a command. Unknown shell constructs fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable
import ast
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
    evidence_kind: str = "exit_status"


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


# Equivalent run-only wrappers observed in native harness sessions. A definition
# alone is never execution evidence. Keep the grammar narrow and non-executable.
RUN_FUNCTION = re.compile(
    r"auto_bean\(\)\s*\{\s*(?:timeout\s+(?P<timeout>[1-9]\d*(?:\.\d+)?[smhd]?)\s+)?"
    r'sh\s+"\$AUTO_BEAN_PLUGIN/runtime/launch.sh"\s+run\s+--workspace\s+'
    r'"\$AUTO_BEAN_WORKSPACE"\s+"\$@"\s*;?\s*\}'
)


def literal_cat_sequence(
    script: str, cwd: str, output: str, exit_code: int
) -> list[tuple[tuple[str, ...], str]]:
    """Inspect complete output from a shell sequence containing only plain cats.

    POSIX cat reports failed operands on stderr. With no redirects, wrappers,
    substitutions or other programs, native combined output preserves those
    diagnostics. This handles mutable files without comparing their later state.
    A failed member of an && chain stops that chain; semicolons start a new one.
    """
    if not output or re.search(
        r"(?:tokens?|characters?|lines?) truncated|output truncated", output, re.I
    ):
        return []
    lexer = shlex.shlex(script, posix=False, punctuation_chars=";&|<>()\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    groups: list[tuple[list[str], str]] = []
    group: list[str] = []
    separator = ";"
    for token in tokens:
        if token in {";", "&&", "\n"}:
            if group:
                groups.append((group, separator))
            group, separator = [], token
        else:
            group.append(token)
    if group:
        groups.append((group, separator))
    commands = []
    for group, separator in groups:
        try:
            argv = shlex.split(" ".join(group))
        except ValueError:
            return []
        if not argv or argv[0] != "cat" or len(argv) < 2:
            return []
        if any(
            not re.fullmatch(r"[A-Za-z0-9_./-]+", arg) or arg.startswith("-")
            for arg in argv[1:]
        ):
            return []
        commands.append((argv, separator))
    diagnostics = [line for line in output.splitlines() if line.startswith("cat:")]
    # An unknown/localized diagnostic or write failure cannot identify successful operands.
    failed = set()
    for line in diagnostics:
        matches = [
            arg
            for argv, _ in commands
            for arg in argv[1:]
            if line.startswith(f"cat: {arg}: ")
        ]
        if not matches:
            return []
        failed.update(matches)
    result: list[tuple[tuple[str, ...], str]] = []
    previous_ok = True
    for argv, separator in commands:
        if separator == "&&" and not previous_ok:
            continue
        previous_ok = not any(arg in failed for arg in argv[1:])
        for arg in argv[1:]:
            if arg not in failed:
                result.append((("cat", absolute(arg, cwd)), cwd))
    return result if previous_ok == (exit_code == 0) else []


def snapshot_reader(ledger: Path, plugin: Path) -> Callable[[str], str | None]:
    """Map container paths to verifier-owned plugin files and saved ledger data.

    Only text is read; no workspace code is imported or executed. A changed
    snapshot cannot prove an earlier read and therefore remains uncredited.
    """

    def read(path: str) -> str | None:
        parts = PurePosixPath(path)
        root, relative = (
            ledger,
            parts.relative_to("/app/ledger")
            if parts.is_relative_to("/app/ledger")
            else None,
        )
        if relative is None:
            for marker in ("/skills/", "/references/"):
                if marker in path:
                    prefix, suffix = path.split(marker, 1)
                    if any(path_matches(prefix, allowed) for allowed in PLUGIN_ROOTS):
                        root, relative = (
                            plugin,
                            PurePosixPath(marker.strip("/"), suffix),
                        )
                        break
        if relative is None:
            return None
        candidate = root / str(relative)
        try:
            if not candidate.resolve().is_relative_to(root.resolve()):
                return None
            return candidate.read_text()
        except (OSError, UnicodeError):
            return None

    return read


def observed_cat_reads(
    script: str, cwd: str, output: str, contents: Callable[[str], str | None]
) -> list[tuple[tuple[str, ...], str]]:
    """Recover literal reads by matching full file contents in native output.

    This supplements exit-status evidence for read-only compound calls. Never
    search arbitrary program output for commands. Only plain cat operands are
    credited; snapshots that changed, empty files, or truncated content cannot
    establish a read. Other supported commands only explain surrounding output.
    """
    lexer = shlex.shlex(script, posix=False, punctuation_chars=";&|<>()\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    groups: list[list[str]] = [[]]
    for token in tokens:
        if token == "&&":
            groups.append([])
        elif token in {";", "\n", "|", "||", "&", "(", ")", ">", ">>", "<", "<<"}:
            return []
        else:
            groups[-1].append(token)
    commands = []
    for group in groups:
        if not group:
            continue
        try:
            argv = shlex.split(" ".join(group))
        except ValueError:
            return []
        if any("$" in arg or "`" in arg for arg in argv):
            return []
        if argv[0] == "cat":
            if len(argv) < 2 or any(arg.startswith("-") for arg in argv[1:]):
                return []
        elif argv[:2] == ["git", "status"]:
            if any(arg not in {"--short", "--porcelain"} for arg in argv[2:]):
                return []
        elif argv[:2] == ["rg", "-n"]:
            # Exclude pre-processors, config injection and other execution options.
            if len(argv) < 4 or any(arg.startswith("-") for arg in argv[2:]):
                return []
        else:
            return []
        commands.append(argv)
    if any(argv[0] == "rg" for argv in commands[:-1]):
        return []
    result: list[tuple[tuple[str, ...], str]] = []
    offset = 0
    for argv in commands:
        if argv[0] != "cat":
            continue
        for operand in argv[1:]:
            path = absolute(operand, cwd)
            content = contents(path)
            if not content or not content.strip():
                continue
            index = output.find(content, offset)
            if index >= 0:
                result.append((("cat", path), cwd))
                offset = index + len(content)
    return result


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
    run_only = False
    helper_timeout: str | None = None

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
            run_only = match is None
            if match is None:
                match = RUN_FUNCTION.search(function_lines)
            helper_timeout = match.group("timeout") if match and run_only else None
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
        if "|" in tokens:
            # A successful final && operand ran even if an earlier read-only
            # pipeline masks its producer's status. Credit only that suffix.
            suffix = readonly_pipeline_suffix(tokens)
            if suffix is not None:
                result = shell_commands(suffix, cwd)
            continue
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
            if expanded[0] == "auto_bean":
                if prefixed or not helper or not variables.get("AUTO_BEAN_PLUGIN"):
                    continue
                launcher = variables["AUTO_BEAN_PLUGIN"] + "/runtime/launch.sh"
                if not run_only and expanded[1:2] == ["validate"]:
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
                if helper_timeout:
                    expanded = ["timeout", helper_timeout, *expanded]
            line_result.append((tuple(expanded), cwd))
        if line_result:
            # Newlines also mask earlier exit statuses. Assignments above still
            # resolve variables, but only the final executable line is credited.
            result = line_result
    return result


def readonly_pipeline_suffix(tokens: list[str]) -> str | None:
    """Recognize a literal read-only prefix and its final && command."""
    if "&&" not in tokens:
        return None
    boundary = len(tokens) - 1 - tokens[::-1].index("&&")
    groups: list[list[str]] = [[]]
    for token in tokens[:boundary]:
        if token in {"&&", "|"}:
            groups.append([])
        else:
            groups[-1].append(token)
    for group in groups:
        try:
            argv = shlex.split(" ".join(group))
        except ValueError:
            return None
        if not argv or any(
            re.search(r"[$`\n]", arg) or arg in {";", "||", "&", "(", ")", ">", "<"}
            for arg in argv
        ):
            return None
        if argv[0] == "rg" and argv[1:2] == ["--files"]:
            valid = all(not arg.startswith("-") for arg in argv[2:])
        elif argv[0] == "cat":
            valid = len(argv) > 1 and all(not arg.startswith("-") for arg in argv[1:])
        elif argv[0] == "head":
            valid = len(argv) == 2 and bool(re.fullmatch(r"-[1-9]\d*", argv[1]))
        elif argv[:2] == ["sed", "-n"]:
            valid = len(argv) >= 4 and bool(re.fullmatch(r"\d+(?:,\d+)?p", argv[2]))
            valid = valid and all(not arg.startswith("-") for arg in argv[3:])
        else:
            valid = False
        if not valid:
            return None
    return " ".join(tokens[boundary + 1 :])


def python_reads(script: str, cwd: str) -> list[str]:
    """Inspect a safe, unconditional Python prefix; never run submitted code.

    Only literal Path constructors and reads reached through known bindings
    count. Stop before unknown calls, mutations or control flow. The caller
    requires a successful native completion of the Python command itself.
    """
    match = re.search(r"<<\s*(['\"]?)(\w+)\1\s*\n", script)
    if match:
        if not match[1]:
            return []
        # No trailing shell command may hide a Python failure.
        end = re.search(rf"(?m)^{re.escape(match[2])}\s*$", script[match.end() :])
        if end is None:
            return []
        body = script[match.end() : match.end() + end.start()]
        if script[match.end() + end.end() :].strip():
            return []
        header = script[: match.start()].rstrip()
        commands = shell_commands(header, cwd)
    else:
        body = ""
        commands = shell_commands(script, cwd)
    if len(commands) != 1:
        return []
    argv, directory = commands[-1]
    if argv[:1] == ("sh",) and len(argv) > 6:
        launcher = argv[1]
        if not any(
            path_matches(launcher, root + "/runtime/launch.sh") for root in PLUGIN_ROOTS
        ) or argv[2:5] != ("run", "--workspace", "/app/ledger"):
            return []
        argv = argv[5:]
    if argv[:1] not in {("python",), ("python3",)}:
        return []
    if match:
        if argv[1:] != ("-",):
            return []
    elif len(argv) == 3 and argv[1] == "-c":
        body = argv[2]
    else:
        return []
    try:
        tree = ast.parse(body)
    except SyntaxError:
        return []
    bindings: dict[str, tuple[str, str]] = {}
    paths: list[str] = []

    def value(node: ast.AST) -> tuple[str, str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return "text", node.value
        if isinstance(node, ast.Name) and node.id in bindings:
            return bindings[node.id]
        if isinstance(node, ast.Attribute):
            owner = value(node.value)
            if (owner, node.attr) == (("module", "pathlib"), "Path"):
                return "constructor", "Path"
            if (owner, node.attr) == (("module", "json"), "loads"):
                return "function", "loads"
            raise ValueError
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "read_text":
                path = value(node.func.value)
                if (
                    path[0] != "path"
                    or node.args
                    or any(
                        k.arg != "encoding" or value(k.value)[0] != "text"
                        for k in node.keywords
                    )
                ):
                    raise ValueError
                paths.append(absolute(path[1], directory))
                return "data", ""
            function = value(node.func)
            if node.keywords or len(node.args) != 1:
                raise ValueError
            argument = value(node.args[0])
            if function == ("constructor", "Path") and argument[0] == "text":
                return "path", argument[1]
            if function == ("function", "loads") and argument[0] == "data":
                return "data", ""
        raise ValueError

    for node in tree.body:
        try:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in {
                        "pathlib",
                        "json",
                        "hashlib",
                        "datetime",
                        "copy",
                    }:
                        raise ValueError
                    bindings[alias.asname or alias.name] = "module", alias.name
            elif isinstance(node, ast.ImportFrom) and node.module == "pathlib":
                for alias in node.names:
                    if alias.name != "Path" or node.level:
                        raise ValueError
                    bindings[alias.asname or alias.name] = "constructor", "Path"
            elif isinstance(node, ast.Assign) and all(
                isinstance(target, ast.Name) for target in node.targets
            ):
                assigned = value(node.value)
                for target in node.targets:
                    assert isinstance(target, ast.Name)
                    bindings[target.id] = assigned
            elif isinstance(node, ast.Expr):
                value(node.value)
            else:
                break
        except ValueError:
            break
    return paths


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
    if name == "python-read" and command.evidence_kind == "native_python_read":
        return list(argv[1:])
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
    if argv[0] in {"sh", "bash"} and len(argv) > 2:
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
    if name == "validate" and "--price-run" in tail:
        # A price-only result cannot establish statement/session validation.
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


def load_commands(
    logs: Path,
    *,
    contents: Callable[[str], str | None] | None = None,
    workers: list[dict[str, Any]] | None = None,
) -> list[Command]:
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
    if workers is not None:
        for path, _, meta in sessions:
            identity = meta.get("id", meta.get("session_id"))
            if identity in allowed and identity != root_id:
                workers.append(
                    {
                        "id": identity,
                        "evidence": f"{path.relative_to(logs)}:1",
                        "source": meta["source"],
                    }
                )
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
                or item.get("status") not in {"completed", "failed"}
                or not isinstance(item.get("exit_code"), int)
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
            observed = (
                [
                    (command, directory, "exit_status")
                    for command, directory in shell_commands(argv[2], cwd)
                ]
                if item["exit_code"] == 0
                else []
            )
            observed.extend(
                (command, directory, "native_cat_diagnostics")
                for command, directory in literal_cat_sequence(
                    argv[2], cwd, item.get("aggregated_output", ""), item["exit_code"]
                )
            )
            if item["exit_code"] == 0:
                observed.extend(
                    (("python-read", path), cwd, "native_python_read")
                    for path in python_reads(argv[2], cwd)
                )
            if contents:
                observed.extend(
                    (command, directory, "native_output_content")
                    for command, directory in observed_cat_reads(
                        argv[2], cwd, item.get("aggregated_output", ""), contents
                    )
                )
            for command, directory, evidence_kind in observed:
                result.append(
                    Command(
                        f"{path.relative_to(logs)}:{line_number}:{item.get('id', '')}",
                        event["timestamp"] >= boundary,
                        command,
                        directory,
                        str(meta.get("id", meta.get("session_id")))
                        if meta.get("id", meta.get("session_id")) != root_id
                        else None,
                        evidence_kind,
                    )
                )
    return result


def grade_trace(
    logs: Path,
    phase: str,
    stage_groups: dict[str, list[dict[str, Any]]] | None = None,
    parsed_paths: list[str] | None = None,
    *,
    contents: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "phase": phase,
        "passed": False,
        "checks": [],
        "workers": [],
    }
    try:
        commands = load_commands(logs, contents=contents, workers=report["workers"])
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
                "detail": ", ".join(sorted({c.evidence_kind for c in matches}))
                if matches
                else "Insufficient recognized execution evidence; this does not prove the action was absent.",
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

    if assignments and all(assignments):
        check(
            "subagents:separate-group-stage-workers",
            [c for c in current if c.agent_id]
            if distinct_workers(sorted(assignments, key=len), set())
            else [],
        )
    elif assignments:
        report["checks"].append(
            {
                "requirement": "subagents:separate-group-stage-workers",
                "passed": False,
                "evidence": [],
                "detail": "Worker identity is recorded in descendant session metadata, but stage/group activity is not fully established. Distinctness is undetermined, not disproven.",
            }
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
