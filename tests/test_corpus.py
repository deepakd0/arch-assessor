"""Real-world Terraform corpus (spec 009 §6).

Weekly-scheduled only (see .github/workflows/corpus.yml) — never per-PR,
since it clones real repositories over the network. This is the primary
discovery mechanism for Phase 2 parser-coverage gaps: a failure here means
some real-world HCL shape the fixture suite doesn't cover yet.

Run manually with: pytest tests/test_corpus.py -m corpus -v
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from archassessor.cli.main import main
from archassessor.ingest.terraform.parser import parse_directory

pytestmark = pytest.mark.corpus

REPOS_FILE = Path(__file__).parent / "corpus" / "repos.txt"

# Warning codes the parser is known to emit (spec 002 §3). Any other code
# appearing against real-world HCL is itself a finding worth investigating.
KNOWN_WARNING_CODES = {"W001", "W002", "W003", "W004", "W005", "W006", "W007", "W008"}


def _read_repos() -> list[tuple[str, str, str]]:
    entries = []
    for line in REPOS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url, sha, name = line.split()
        entries.append((url, sha, name))
    return entries


def _clone_at(url: str, sha: str, dest: Path) -> None:
    subprocess.run(["git", "init", "-q", str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "remote", "add", "origin", url], check=True)
    subprocess.run(
        ["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", sha], check=True
    )
    subprocess.run(["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"], check=True)


@pytest.mark.parametrize("url,sha,name", _read_repos() if REPOS_FILE.exists() else [])
def test_corpus_repo_parses_without_crashing(url: str, sha: str, name: str, tmp_path: Path) -> None:
    repo_dir = tmp_path / name
    _clone_at(url, sha, repo_dir)

    result = parse_directory(repo_dir)  # must never raise
    unknown_codes = {w.code for w in result.warnings} - KNOWN_WARNING_CODES
    assert not unknown_codes, f"{name}: unrecognized warning codes {unknown_codes}"

    exit_code = main(["scan", str(repo_dir), "--fail-on", "never", "-q"])
    assert exit_code in {0, 1}, f"{name}: unexpected exit code {exit_code}"
