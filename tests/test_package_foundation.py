from __future__ import annotations

from pathlib import Path


def test_package_foundation_layout_and_entrypoint() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src" / "auto_bean"

    assert src_root.is_dir()
    assert (src_root / "__init__.py").is_file()
    assert (src_root / "__main__.py").is_file()

    for package_dir in ("cli", "application", "domain", "infrastructure", "memory"):
        assert (src_root / package_dir).is_dir()
        assert (src_root / package_dir / "__init__.py").is_file()

    from auto_bean import main

    assert callable(main)
