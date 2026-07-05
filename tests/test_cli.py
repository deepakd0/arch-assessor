"""Spec 006 end-to-end tests: exit codes, stream discipline, determinism."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import TF

from archassessor.cli.main import main


def test_scan_markdown_to_stdout(capsys) -> None:
    code = main(["scan", str(TF / "simple")])
    out, err = capsys.readouterr()
    assert out.startswith("# Architecture Assessment Report")
    assert "scanned 4 resources" in err
    # simple/ has high fails (multi_az false, owner tags missing is medium…)
    assert code == 1  # default --fail-on high


def test_fail_on_matrix(capsys) -> None:
    path = str(TF / "simple")
    assert main(["scan", path, "--fail-on", "critical", "-q"]) == 0
    assert main(["scan", path, "--fail-on", "any", "-q"]) == 1
    assert main(["scan", path, "--fail-on", "never", "-q"]) == 0
    capsys.readouterr()


def test_json_output_file_deterministic(tmp_path: Path, capsys) -> None:
    out1, out2 = tmp_path / "a.json", tmp_path / "b.json"
    main(["scan", str(TF / "simple"), "--format", "json", "-o", str(out1), "-q"])
    main(["scan", str(TF / "simple"), "--format", "json", "-o", str(out2), "-q"])
    stdout, _ = capsys.readouterr()
    assert stdout == ""  # report went to the file, not stdout
    assert out1.read_bytes() == out2.read_bytes()
    payload = json.loads(out1.read_text())
    assert "generated_at" not in payload
    assert payload["summary"]["nodes_total"] == 4


def test_nonexistent_path_is_usage_error(capsys) -> None:
    code = main(["scan", "definitely/not/here"])
    out, err = capsys.readouterr()
    assert code == 2 and out == "" and err.startswith("error:")


def test_invalid_rules_dir_is_input_error(capsys) -> None:
    fixtures = Path(__file__).parent / "fixtures" / "rules_bad"
    code = main(["scan", str(TF / "simple"), "--rules", str(fixtures)])
    _, err = capsys.readouterr()
    assert code == 3
    assert "duplicate rule id" in err and "severity" in err


def test_no_rules_at_all_is_usage_error(capsys) -> None:
    code = main(["scan", str(TF / "simple"), "--no-builtin"])
    _, err = capsys.readouterr()
    assert code == 2 and "no rules loaded" in err


def test_broken_repo_still_scans_with_warning(capsys) -> None:
    code = main(["scan", str(TF / "broken")])
    _, err = capsys.readouterr()
    assert code in (0, 1)
    assert "warning W001 bad.tf" in err
    code = main(["scan", str(TF / "broken"), "--quiet"])
    _, err = capsys.readouterr()
    assert err == ""
    assert code in (0, 1)


def test_graph_command_matches_parser_output(capsys) -> None:
    code = main(["graph", str(TF / "simple"), "-q"])
    out, _ = capsys.readouterr()
    assert code == 0
    payload = json.loads(out)
    assert payload["schema_version"] == "1.0"
    assert len(payload["nodes"]) == 4


def test_rules_list_table_and_json(capsys) -> None:
    assert main(["rules", "list"]) == 0
    out, _ = capsys.readouterr()
    assert "BASE-SEC-001" in out and out.startswith("ID")

    assert main(["rules", "list", "--format", "json"]) == 0
    out, _ = capsys.readouterr()
    payload = json.loads(out)
    ids = [r["id"] for r in payload]
    assert ids == sorted(ids) and "BASE-SEC-001" in ids


def test_version_and_help(capsys) -> None:
    with_version = main(["--version"])
    out, _ = capsys.readouterr()
    assert with_version == 0 and out.startswith("archscan ")
    assert main(["scan", "--help"]) == 0
    capsys.readouterr()


def test_framework_filter_limits_readiness_section(capsys) -> None:
    code = main(["scan", str(TF / "simple"), "--framework", "pci_dss", "-q"])
    out, _ = capsys.readouterr()
    assert code in (0, 1)
    assert "### SOC 2" not in out
