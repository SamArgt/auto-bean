"""Prepare dependency PRs and merge only verified, non-eval updates."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

MANIFEST = "plugins/auto-bean/plugin.json"
RUNTIME = "plugins/auto-bean/runtime"
FRONTEND = "frontend/import-review"
PROJECTS = ("pyproject.toml", f"{RUNTIME}/pyproject.toml")
LOCKS = ("uv.lock", f"{RUNTIME}/uv.lock")
GENERATED = {
    MANIFEST,
    "plugins/auto-bean/ui/bundle.html",
    "plugins/auto-bean/ui/build.json",
}
CHECKS = {"quality-baseline (ubuntu-latest)", "quality-baseline (macos-latest)"}
SAFE_TYPES = {"minor", "patch", "pin", "pinDigest", "digest", "lockFileMaintenance"}


def dashboard_requested(event: dict[str, Any]) -> bool:
    """Accept new checked Renovate actions, not text edits or unchecked boxes."""
    previous = event.get("changes", {}).get("body", {}).get("from")
    current = event.get("issue", {}).get("body")
    if not isinstance(previous, str) or not isinstance(current, str):
        return False
    pattern = re.compile(
        r"(?m)^\s*- \[([ xX])\] <!-- "
        r"((?:unlimit-branch|rebase-branch|approve-branch|approvePr-branch)=\S+|"
        r"create-all-rate-limited-prs|rebase-all-open-prs|approve-all-pending-prs) -->"
    )
    unchecked = {action for state, action in pattern.findall(previous) if state == " "}
    checked = {action for state, action in pattern.findall(current) if state != " "}
    return bool(unchecked & checked)


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def git(*args: str) -> str:
    return command("git", *args)


def read_at(ref: str, path: str) -> str:
    return git("show", f"{ref}:{path}")


def semver(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value):
        raise ValueError(f"Expected a stable release version: {value}")
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def write_json(path: str, data: Any) -> None:
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def replace_version(path: str, pattern: str, version: str) -> None:
    def replacement(match: re.Match[str]) -> str:
        return match[1] + version + match[2]

    text, count = re.subn(pattern, replacement, Path(path).read_text())
    if count != 1:
        raise ValueError(f"Expected one project version in {path}; found {count}")
    Path(path).write_text(text)


def prepare(base_ref: str) -> None:
    sync_python()
    base = git("rev-parse", "--verify", f"{base_ref}^{{commit}}")
    major, minor, patch = semver(json.loads(read_at(base, MANIFEST))["version"])
    version = f"{major}.{minor}.{patch + 1}"
    manifest = json.loads(Path(MANIFEST).read_text())
    manifest["version"] = version
    write_json(MANIFEST, manifest)
    for path in PROJECTS:
        replace_version(path, r'(?m)(^version = ")[^"]+("$)', version)
    # Change only the local project entry. Preserve Renovate's resolved updates.
    for path, name in zip(LOCKS, ("auto-bean-dev", "auto-bean-runtime"), strict=True):
        replace_version(path, rf'(name = "{name}"\nversion = ")[^"]+(")', version)
    for path in (f"{FRONTEND}/package.json", f"{FRONTEND}/package-lock.json"):
        data = json.loads(Path(path).read_text())
        data["version"] = version
        if "packages" in data:
            data["packages"][""]["version"] = version
        write_json(path, data)
    # Lock after all declarations and release versions are in sync. Do not use
    # --upgrade: keep Renovate's unrelated resolved versions.
    for project in (".", RUNTIME):
        subprocess.run(["uv", "lock", "--project", project], check=True)
    package = json.loads(Path(f"{FRONTEND}/package.json").read_text())
    manager = package["packageManager"]
    if not re.fullmatch(r"npm@\d+\.\d+\.\d+", manager):
        raise ValueError("The frontend must select an exact npm version")
    npm = ["npx", "--yes", "--package", manager, "--", "npm", "--prefix", FRONTEND]
    subprocess.run(
        [*npm, "install", "--package-lock-only", "--ignore-scripts"], check=True
    )
    subprocess.run([*npm, "ci", "--ignore-scripts"], check=True)
    subprocess.run([*npm, "run", "build"], check=True)
    subprocess.run([*npm, "test"], check=True)
    print(f"Prepared plugin {version} above {base}.")


def sync_python() -> None:
    """Use the root Python requirement for every executable Python pin."""
    project = tomllib.loads(Path("pyproject.toml").read_text())
    requirement = project["project"]["requires-python"]
    match = re.fullmatch(r">=(\d+\.\d+(?:\.\d+)?),\s*<\d+\.\d+", requirement)
    if not match:
        raise ValueError(f"Unsupported Python requirement: {requirement}")
    version = match[1]
    minor = ".".join(version.split(".")[:2])
    replace_version(
        f"{RUNTIME}/pyproject.toml",
        r'(?m)(^requires-python = ")[^"]+("$)',
        requirement,
    )
    for path in (".python-version", f"{RUNTIME}/.python-version"):
        Path(path).write_text(version + "\n")
    replace_version("pyproject.toml", r'(?m)(^python_version = ")[^"]+("$)', minor)
    replace_version(
        "pyproject.toml",
        r'(?m)(^target-version = ")[^"]+("$)',
        "py" + minor.replace(".", ""),
    )
    replace_version(
        "evals/harbor/environment/Dockerfile",
        r"(?m)(^ENV UV_PYTHON=)[^\n]+($)",
        version,
    )


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(value: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", value)
    if not match:
        raise ValueError(f"Unknown requirement: {value}")
    return normalized(match[0])


def locked_eval(text: str, names: set[str]) -> list[str]:
    return sorted(
        json.dumps(
            {
                key: package.get(key)
                for key in ("name", "version", "source", "resolution-markers")
            },
            sort_keys=True,
        )
        for package in tomllib.loads(text)["package"]
        if normalized(package["name"]) in names
    )


def dependency_shape(project: dict[str, Any]) -> dict[str, Any]:
    """Remove versions, but preserve names and all non-dependency settings."""
    project["project"].pop("version", None)
    for group in (
        project.get("dependency-groups", {}),
        project["project"].get("optional-dependencies", {}),
    ):
        for key, requirements in group.items():
            group[key] = [requirement_name(item) for item in requirements]
    if "dependencies" in project["project"]:
        project["project"]["dependencies"] = [
            requirement_name(item) for item in project["project"]["dependencies"]
        ]
    return project


def package_shape(package: dict[str, Any]) -> dict[str, Any]:
    package.pop("version", None)
    for key in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        if key in package:
            package[key] = sorted(package[key])
    return package


def versions(path: str, text: str) -> dict[str, set[str]]:
    if path.endswith("uv.lock"):
        entries = [
            (item["name"], item["version"])
            for item in tomllib.loads(text)["package"]
            if "virtual" not in item["source"]
        ]
    else:
        entries = [
            (name, item["version"])
            for name, item in json.loads(text)["packages"].items()
            if name and "version" in item
        ]
    result: dict[str, set[str]] = {}
    for name, version in entries:
        result.setdefault(name, set()).add(version)
    return result


def lock_update_reason(path: str, before: str, after: str) -> str | None:
    old, new = versions(path, before), versions(path, after)
    for name in old.keys() & new.keys():
        if old[name] == new[name]:
            continue
        # A newly introduced major in an existing package needs human review.
        # New transitive packages have no previous version to compare.
        if not all(re.match(r"^\d+\.", value) for value in old[name] | new[name]):
            return f"Unknown locked version for {name}"
        old_majors = {value.split(".")[0] for value in old[name]}
        if any(value.split(".")[0] not in old_majors for value in new[name]):
            return f"Major locked update: {name}"
    return None


def policy_reason(base: str, head: str, message: str) -> str | None:
    markers = re.findall(r"^Auto-Bean-Update-Types:([^\n]*)$", message, re.MULTILINE)
    if (
        len(markers) != 1
        or not markers[0].split()
        or not set(markers[0].split()) <= SAFE_TYPES
    ):
        return "Major or unclassified update"
    old_project = tomllib.loads(read_at(base, "pyproject.toml"))
    new_project = tomllib.loads(read_at(head, "pyproject.toml"))
    old_eval = old_project["dependency-groups"]["eval"]
    new_eval = new_project["dependency-groups"]["eval"]
    if old_eval != new_eval:
        return "Direct eval declarations changed"
    names = {requirement_name(item) for item in old_eval + new_eval}
    for path in LOCKS:
        if locked_eval(read_at(base, path), names) != locked_eval(
            read_at(head, path), names
        ):
            return f"Direct eval lock entries changed: {path}"
    for path in git("diff", "--name-only", base, head).splitlines():
        if path.startswith("evals/"):
            return "Eval tool or container changed"
        if path in GENERATED:
            continue
        if path not in (
            *PROJECTS,
            *LOCKS,
            f"{FRONTEND}/package.json",
            f"{FRONTEND}/package-lock.json",
        ) and not (path.startswith(".github/workflows/") and path.endswith(".yml")):
            return f"Unexpected file: {path}"
        before, after = read_at(base, path), read_at(head, path)
        if path in PROJECTS:
            if dependency_shape(tomllib.loads(before)) != dependency_shape(
                tomllib.loads(after)
            ):
                return f"Non-dependency project change: {path}"
        elif path == f"{FRONTEND}/package.json":
            if package_shape(json.loads(before)) != package_shape(json.loads(after)):
                return "Non-dependency frontend change"
        elif path in (*LOCKS, f"{FRONTEND}/package-lock.json"):
            reason = lock_update_reason(path, before, after)
            if reason:
                return reason
        elif path.startswith(".github/workflows/") and path.endswith(".yml"):
            pattern = r"(?m)^(\s*(?:- )?uses: )[\w./-]+@[^\s]+(?:\s+#.*)?$"
            before = re.sub(
                r"--package renovate@[0-9.]+", "--package renovate@VERSION", before
            )
            after = re.sub(
                r"--package renovate@[0-9.]+", "--package renovate@VERSION", after
            )
            if re.sub(pattern, r"\1ACTION", before) != re.sub(
                pattern, r"\1ACTION", after
            ):
                return "Workflow changes beyond action versions"
    if semver(json.loads(read_at(head, MANIFEST))["version"]) <= semver(
        json.loads(read_at(base, MANIFEST))["version"]
    ):
        return "Plugin version did not increase"
    return None


def api(path: str, *args: str) -> Any:
    return json.loads(command("gh", "api", path, *args))


def checks_pass(runs: list[dict[str, Any]], head: str) -> bool:
    latest: dict[str, dict[str, Any]] = {}
    for run in sorted(runs, key=lambda item: item["id"]):
        if run["app"]["slug"] == "github-actions" and run["head_sha"] == head:
            latest[run["name"]] = run
    return all(
        name in latest
        and latest[name]["status"] == "completed"
        and latest[name]["conclusion"] == "success"
        for name in CHECKS
    )


def merge() -> None:
    repository, bot = os.environ["GITHUB_REPOSITORY"], os.environ["RENOVATE_BOT"]
    endpoint = f"repos/{repository}"
    pulls = api(f"{endpoint}/pulls?state=open&base=main&per_page=100")
    for summary in pulls:
        if summary["user"]["login"] != bot or not summary["head"]["ref"].startswith(
            "renovate/"
        ):
            continue
        number = summary["number"]
        pr = api(f"{endpoint}/pulls/{number}")
        if (
            pr["draft"]
            or pr["head"]["repo"]["full_name"] != repository
            or pr["mergeable"] is not True
        ):
            continue
        base, head = pr["base"]["sha"], pr["head"]["sha"]
        commits = api(f"{endpoint}/pulls/{number}/commits?per_page=100")
        if (
            len(commits) != 1
            or commits[0]["sha"] != head
            or (commits[0].get("author") or {}).get("login") != bot
        ):
            print(f"PR #{number}: manual merge; branch has non-Renovate commits.")
            continue
        subprocess.run(["git", "fetch", "origin", base, head], check=True)
        if git("merge-base", base, head) != base:
            print(f"PR #{number}: waiting for a rebase.")
            continue
        try:
            reason = policy_reason(base, head, commits[0]["commit"]["message"])
        except (
            ValueError,
            KeyError,
            TypeError,
            subprocess.CalledProcessError,
        ) as error:
            reason = f"Cannot classify changes: {error}"
        if reason:
            print(f"PR #{number}: manual merge; {reason}.")
            continue
        runs = api(f"{endpoint}/commits/{head}/check-runs?per_page=100")["check_runs"]
        if not checks_pass(runs, head):
            print(f"PR #{number}: waiting for both baseline checks.")
            continue
        if api(f"{endpoint}/commits/{head}/status")["state"] != "success":
            print(f"PR #{number}: waiting for dependency preparation status.")
            continue
        # GitHub also enforces the strict checks ruleset at merge time.
        if api(f"{endpoint}/commits/main")["sha"] != base:
            return
        result = api(
            f"{endpoint}/pulls/{number}/merge",
            "--method",
            "PUT",
            "-f",
            f"sha={head}",
            "-f",
            "merge_method=squash",
        )
        if not result.get("merged"):
            raise ValueError(f"GitHub refused PR #{number}: {result.get('message')}")
        print(f"Merged PR #{number} at {head}.")
        return  # Rebase other PRs on the next run before assigning their versions.


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    preparation = commands.add_parser("prepare")
    preparation.add_argument("--base-ref", required=True)
    commands.add_parser("merge")
    commands.add_parser("dashboard-request")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.base_ref)
    elif args.action == "dashboard-request":
        requested = dashboard_requested(
            json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        )
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            output.write(f"requested={str(requested).lower()}\n")
    else:
        merge()


if __name__ == "__main__":
    main()
