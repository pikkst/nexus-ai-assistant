"""Packaging smoke tests for the Nexus assistant."""

from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_pyproject_toml_is_valid() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = data["project"]
    assert project["name"] == "nexus"
    assert project["requires-python"] == ">=3.11"
    scripts = project.get("scripts", {})
    assert "nexus" in scripts
    assert scripts["nexus"] == "src.main:main"


def test_entry_point_module_importable() -> None:
    main = importlib.import_module("src.main")
    assert hasattr(main, "main")


def test_core_packages_importable() -> None:
    packages = [
        "src",
        "src.app",
        "src.audio",
        "src.config",
        "src.llm",
        "src.memory",
        "src.stt",
        "src.tts",
        "src.ui",
        "src.vision",
    ]
    for name in packages:
        importlib.import_module(name)
