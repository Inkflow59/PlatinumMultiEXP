"""Shared test setup.

Tests that need real ROMs read their paths from PLATINUM_ROMS, a list separated by
os.pathsep (";" on Windows, ":" elsewhere). Without it, those tests are skipped.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

ROM_PATHS = [p for p in os.environ.get("PLATINUM_ROMS", "").split(os.pathsep) if p]


def pytest_generate_tests(metafunc):
    if "rom_path" in metafunc.fixturenames:
        metafunc.parametrize("rom_path", ROM_PATHS or [None], ids=[Path(p).stem for p in ROM_PATHS] or ["no-rom"])


def pytest_collection_modifyitems(config, items):
    import pytest

    skip = pytest.mark.skip(reason="PLATINUM_ROMS not set")
    for item in items:
        callspec = getattr(item, "callspec", None)
        if callspec is not None and callspec.params.get("rom_path", "x") is None:
            item.add_marker(skip)
