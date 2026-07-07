"""Golden-file tests (spec 005 §7.1, acceptance criterion 1).

A hand-built Assessment — independent of the evolving builtin rule pack —
covering every severity, an unknown, all four framework-control statuses,
and a not-applicable rule. Rendered output is compared byte-for-byte against
checked-in fixtures. Also exercises the "nothing to report" branches via a
second, empty assessment.

Regenerate deliberately (never blindly) with:
    ARCHASSESSOR_WRITE_GOLDEN=1 pytest tests/test_report_golden.py
and review the diff before committing.
"""

from __future__ import annotations

import os
from pathlib import Path

from archassessor.engine.evaluate import (
    Assessment,
    Finding,
    FrameworkControlStatus,
    RuleResult,
    Summary,
)
from archassessor.graph.model import SourceRef
from archassessor.report import render_html, render_json, render_markdown

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "reports"


def _finding(
    rule_id: str,
    severity: str,
    verdict: str,
    node_id: str,
    node_type: str,
    mappings: dict[str, list[str]] | None = None,
    source: SourceRef | None = None,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_title=f"Golden rule {rule_id}",
        severity=severity,
        category="security",
        description=f"Why {rule_id} matters.",
        node_id=node_id,
        node_name=node_id.rsplit(".", 1)[-1],
        node_type=node_type,
        verdict=verdict,
        detail=f"`prop` is false (expected true) for {rule_id}",
        remediation=f"Fix {rule_id} by setting the property to true.",
        mappings=mappings or {},
        source=source or SourceRef(ingestor="golden", file="main.tf", line=1),
    )


def _rich_assessment() -> Assessment:
    findings = [
        _finding(
            "GOLD-SEC-001",
            "critical",
            "fail",
            "tf:root:aws_s3_bucket.a",
            "storage",
            {"soc2": ["CC6.1"]},
        ),
        _finding(
            "GOLD-SEC-002",
            "high",
            "fail",
            "tf:root:aws_db_instance.b",
            "database",
            {"soc2": ["CC6.6"]},
        ),
        _finding(
            "GOLD-SEC-003",
            "medium",
            "fail",
            "tf:root:aws_kms_key.c",
            "kms_key",
            {"soc2": ["CC6.1"]},
        ),
        _finding("GOLD-SEC-004", "low", "fail", "tf:root:aws_s3_bucket.d", "storage"),
        _finding(
            "GOLD-NET-001",
            "info",
            "fail",
            "tf:root:aws_lb.e",
            "load_balancer",
            source=SourceRef(ingestor="golden", file=None),  # no location and no mappings
        ),
        _finding(
            "GOLD-SEC-005",
            "high",
            "unknown",
            "tf:root:aws_db_instance.f",
            "database",
            {"soc2": ["CC7.2"]},
        ),
    ]
    results = [
        RuleResult(rule_id=f.rule_id, node_id=f.node_id, verdict=f.verdict, detail=f.detail)
        for f in findings
    ] + [
        RuleResult(rule_id="GOLD-SEC-006", node_id="tf:root:aws_vpc.g", verdict="pass", detail="ok")
    ]
    frameworks = [
        FrameworkControlStatus("soc2", "CC6.1", "gap", ["GOLD-SEC-001", "GOLD-SEC-003"]),
        FrameworkControlStatus("soc2", "CC6.6", "gap", ["GOLD-SEC-002"]),
        FrameworkControlStatus("soc2", "CC7.2", "unknown", ["GOLD-SEC-005"]),
        FrameworkControlStatus("soc2", "CC9.9", "not_assessed", ["GOLD-OPS-999"]),
        FrameworkControlStatus("soc2", "CC1.1", "satisfied", ["GOLD-SEC-006"]),
        FrameworkControlStatus("iso27001", "A.8.24", "gap", ["GOLD-SEC-001"]),
    ]
    summary = Summary(
        nodes_total=8,
        rules_evaluated=7,
        rules_not_applicable=1,
        results_pass=1,
        results_fail=5,
        results_unknown=1,
        findings_by_severity={"critical": 1, "high": 2, "medium": 1, "low": 1, "info": 1},
        score=100 - 15 - 10 - 5 - 2 - 5,  # 4 fails + 1 unknown-high(half) = 63
    )
    return Assessment(
        graph_metadata={"ingestor": "golden", "source_root": "fixture"},
        results=results,
        findings=findings,
        not_applicable_rule_ids=["GOLD-OPS-999"],
        summary=summary,
        frameworks=frameworks,
    )


def _empty_assessment() -> Assessment:
    return Assessment(
        graph_metadata={"ingestor": "golden", "source_root": "empty"},
        results=[],
        findings=[],
        not_applicable_rule_ids=[],
        summary=Summary(
            nodes_total=0,
            rules_evaluated=0,
            rules_not_applicable=0,
            results_pass=0,
            results_fail=0,
            results_unknown=0,
            findings_by_severity={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            score=100,
        ),
        frameworks=[],
    )


def _check_or_write(name: str, actual: str) -> None:
    path = GOLDEN_DIR / name
    if os.environ.get("ARCHASSESSOR_WRITE_GOLDEN"):
        path.write_text(actual, encoding="utf-8")
        return
    expected = path.read_text(encoding="utf-8")
    assert actual == expected, f"{name} does not match the golden file byte-for-byte"


def test_golden_markdown_rich() -> None:
    _check_or_write("rich.md", render_markdown(_rich_assessment()))


def test_golden_html_rich() -> None:
    _check_or_write("rich.html", render_html(_rich_assessment()))


def test_golden_json_rich() -> None:
    _check_or_write("rich.json", render_json(_rich_assessment()))


def test_golden_markdown_rich_with_passes() -> None:
    _check_or_write("rich_with_passes.md", render_markdown(_rich_assessment(), include_passes=True))


def test_golden_html_rich_with_passes() -> None:
    _check_or_write("rich_with_passes.html", render_html(_rich_assessment(), include_passes=True))


def test_golden_markdown_empty() -> None:
    _check_or_write("empty.md", render_markdown(_empty_assessment()))


def test_golden_html_empty() -> None:
    _check_or_write("empty.html", render_html(_empty_assessment()))


def test_golden_markdown_empty_with_passes() -> None:
    # No passing results at all -> the "None." branch of include_passes.
    _check_or_write(
        "empty_with_passes.md", render_markdown(_empty_assessment(), include_passes=True)
    )


def test_golden_html_empty_with_passes() -> None:
    _check_or_write("empty_with_passes.html", render_html(_empty_assessment(), include_passes=True))


def test_golden_json_empty() -> None:
    _check_or_write("empty.json", render_json(_empty_assessment()))


def test_golden_files_are_byte_stable_across_runs() -> None:
    # Renderers must be pure: rendering twice from equal (not identical) objects
    # yields identical bytes, independent of the golden fixture check above.
    assert render_markdown(_rich_assessment()) == render_markdown(_rich_assessment())
    assert render_html(_rich_assessment()) == render_html(_rich_assessment())
    assert render_json(_rich_assessment()) == render_json(_rich_assessment())
