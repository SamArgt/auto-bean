"""Validate and reproducibly archive the canonical plugin directory."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
import zipfile
from hashlib import sha256
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/auto-bean"
EXCLUDED = {
    "__pycache__",
    ".venv",
    ".DS_Store",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}


def files(plugin: Path) -> list[Path]:
    result = []
    for path in sorted(plugin.rglob("*")):
        if any(part in EXCLUDED for part in path.relative_to(plugin).parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Plugin files must not be symlinks: {path}")
        if path.is_file() and path.suffix not in {".pyc", ".pyo"}:
            result.append(path)
    return result


def validate_plugin(plugin: Path = PLUGIN) -> str:
    manifest = json.loads((plugin / "plugin.json").read_text())
    if (
        manifest.get("$schema")
        != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    ):
        raise ValueError("Plugin schema declaration missing")
    if manifest.get("name") != "auto-bean" or not re.fullmatch(
        r"\d+\.\d+\.\d+", manifest["version"]
    ):
        raise ValueError("Expected stable auto-bean identity and SemVer version")
    version: str = manifest["version"]
    subtitle = manifest["extensions"]["com.openai"]["interface"]["shortDescription"]
    if not isinstance(subtitle, str) or not 1 <= len(subtitle) <= 30:
        raise ValueError("Plugin subtitle must contain 1-30 characters")
    runtime = tomllib.loads((plugin / "runtime/pyproject.toml").read_text())
    lock = tomllib.loads((plugin / "runtime/uv.lock").read_text())
    if runtime["project"]["version"] != version:
        raise ValueError("Plugin and runtime versions disagree")
    package = next(
        item for item in lock["package"] if item["name"] == "auto-bean-runtime"
    )
    if package["version"] != version:
        raise ValueError("Runtime lockfile version is stale")
    mcp = json.loads((plugin / "mcp.json").read_text())
    service = mcp["mcpServers"]["import-review"]
    if service.get("type") != "stdio" or service.get("args") != [
        "${PLUGIN_ROOT}/runtime/launch.sh",
        "serve",
    ]:
        raise ValueError("Review service must use the bundled stdio launcher")
    build = json.loads((plugin / "ui/build.json").read_text())
    if (
        sha256((plugin / "ui/bundle.html").read_bytes()).hexdigest()
        != build["bundle_sha256"]
    ):
        raise ValueError("Review UI bundle does not match its build evidence")
    source = ROOT / "frontend/import-review"
    if plugin.resolve() == PLUGIN.resolve():
        expected_inputs = {
            "package.json",
            "package-lock.json",
            "tsconfig.json",
            "build.mjs",
            *(
                path.relative_to(source).as_posix()
                for path in (source / "src").rglob("*")
                if path.is_file()
            ),
        }
        if set(build["inputs"]) != expected_inputs:
            raise ValueError("Review UI source inventory changed; rebuild the frontend")
        for relative, expected in build["inputs"].items():
            path = source / relative
            if not path.is_file() or sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(
                    f"Review UI bundle is stale: {relative}; rebuild the frontend"
                )
    onboarding = manifest["extensions"]["com.openai"]["onboardingSkill"]
    if not (plugin / onboarding).is_file():
        raise ValueError("Onboarding skill is missing")
    names = set()
    for path in files(plugin):
        if path.name.endswith(".schema.json"):
            Draft202012Validator.check_schema(json.loads(path.read_text()))
        if path.name == "SKILL.md":
            header = yaml.safe_load(path.read_text().split("---", 2)[1])
            name = header["name"]
            if (
                name != path.parent.name
                or not header.get("description")
                or name in names
            ):
                raise ValueError(f"Invalid skill metadata: {path}")
            names.add(name)
            metadata_path = path.parent / "agents/openai.yaml"
            if metadata_path.exists():
                metadata = yaml.safe_load(metadata_path.read_text())
                if not isinstance(
                    metadata.get("policy", {}).get("allow_implicit_invocation", True),
                    bool,
                ):
                    raise ValueError(f"Invalid invocation policy: {metadata_path}")
        if path.suffix == ".md":
            text = path.read_text()
            if ".agents/skills/" in text:
                raise ValueError(f"Stale installed skill reference: {path}")
            # Check local links and code-form resource paths, preserving workspace data paths.
            references = re.findall(r"\]\(([^)\s]+)\)", text)
            references += re.findall(r"`((?:\.\./|references/)[^`\s]+)`", text)
            for reference in references:
                if "://" in reference or reference.startswith("#") or "*" in reference:
                    continue
                target = (path.parent / reference.split("#", 1)[0]).resolve()
                if not target.is_relative_to(plugin.resolve()) or not target.is_file():
                    raise ValueError(
                        f"Missing or external packaged reference: {path}: {reference}"
                    )
    if len(names) != 9:
        raise ValueError(f"Expected nine skills, found {len(names)}")
    return version


def package_plugin(destination: Path, plugin: Path = PLUGIN) -> Path:
    validate_plugin(plugin)
    if destination.resolve().is_relative_to(plugin.resolve()):
        raise ValueError("Write the archive outside the packaged directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files(plugin):
            info = zipfile.ZipInfo(
                path.relative_to(plugin).as_posix(), date_time=(2026, 1, 1, 0, 0, 0)
            )
            info.create_system = 3
            info.external_attr = (0o100755 if path.suffix == ".sh" else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    version = validate_plugin()
    if args.check:
        print(
            f"Plugin {version}: metadata, nine skills, locked runtime, and references validated."
        )
    else:
        print(package_plugin(ROOT / "dist" / f"auto-bean-{version}.zip"))


if __name__ == "__main__":
    main()
