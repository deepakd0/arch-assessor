"""Performance budgets (spec 007 §1 NFR-P1..P3, spec 009 §5).

Marked `benchmark` so CI runs them on Linux only (spec 009 §5); skip locally
with `pytest -m "not benchmark"` if you're iterating on something else.
Timings use a 2x tolerance over the spec targets to absorb runner noise, per
spec 009 §5's own stated policy.
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

import pytest
from gen_fixture import generate

from archassessor.cli.main import main

pytestmark = pytest.mark.benchmark

NFR_P1_SECONDS = 10 * 2  # 1,000 resources
NFR_P2_SECONDS = 30 * 2  # 5,000 resources
NFR_P3_BYTES = 512 * 1024 * 1024 * 2  # peak memory


def _run_scan(tmp_path: Path, resource_count: int) -> tuple[float, int]:
    repo = tmp_path / f"repo_{resource_count}"
    generate(repo, resource_count)
    out = tmp_path / f"out_{resource_count}.json"

    started = time.monotonic()
    code = main(["scan", str(repo), "--format", "json", "-o", str(out), "-q", "--fail-on", "never"])
    elapsed = time.monotonic() - started

    assert code == 0
    return elapsed, resource_count


def test_scan_1000_resources_within_budget(tmp_path: Path) -> None:
    elapsed, _ = _run_scan(tmp_path, 1000)
    assert elapsed < NFR_P1_SECONDS, (
        f"1,000-resource scan took {elapsed:.1f}s (budget {NFR_P1_SECONDS}s)"
    )


def test_scan_5000_resources_within_budget(tmp_path: Path) -> None:
    elapsed, _ = _run_scan(tmp_path, 5000)
    assert elapsed < NFR_P2_SECONDS, (
        f"5,000-resource scan took {elapsed:.1f}s (budget {NFR_P2_SECONDS}s)"
    )


def test_scan_5000_resources_peak_memory_within_budget(tmp_path: Path) -> None:
    repo = tmp_path / "repo_mem"
    generate(repo, 5000)
    out = tmp_path / "out_mem.json"

    tracemalloc.start()
    code = main(["scan", str(repo), "--format", "json", "-o", str(out), "-q", "--fail-on", "never"])
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert code == 0
    assert peak < NFR_P3_BYTES, (
        f"peak memory {peak / 1024 / 1024:.0f} MB (budget {NFR_P3_BYTES / 1024 / 1024:.0f} MB)"
    )
