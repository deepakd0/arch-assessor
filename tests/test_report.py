"""Spec 005 acceptance tests: structure, XSS, disclaimer, determinism."""

from __future__ import annotations

import json

from conftest import mk_graph, mk_node, mk_rule

from archassessor.engine.evaluate import evaluate
from archassessor.report import DISCLAIMER, render_html, render_json, render_markdown
from archassessor.rules.schema import Leaf


def _assessment():
    nodes = [
        mk_node(
            node_id="tf:root:aws_s3_bucket.evil",
            node_type="storage",
            name="<script>alert(1)</script>",
            public_access_blocked=False,
        ),
        mk_node(node_id="tf:root:aws_db_instance.d", encryption_at_rest=None),
    ]
    rules = [
        mk_rule(
            "TEST-SEC-001",
            "storage",
            Leaf(property="public_access_blocked", operator="equals", operand=True),
            "critical",
            mappings={"soc2": ["CC6.6"]},
        ),
        mk_rule(
            "TEST-SEC-002",
            "database",
            Leaf(property="encryption_at_rest", operator="equals", operand=True),
            "high",
            mappings={"soc2": ["CC6.1"]},
        ),
        mk_rule("TEST-SEC-003", "cdn"),  # not applicable
    ]
    return evaluate(mk_graph(nodes), rules)


def test_markdown_structure() -> None:
    text = render_markdown(_assessment())
    assert text.startswith("# Architecture Assessment Report")
    for section in (
        "## Summary",
        "## Findings",
        "### Critical",
        "### Needs data (unknown)",
        "## Compliance readiness",
        "### SOC 2",
        "## Rules not applicable to this architecture",
        "## About this assessment",
    ):
        assert section in text, section
    assert "TEST-SEC-003" in text
    assert "⚠ gap" in text and "? unknown" in text
    assert "### High" not in text  # high finding is unknown-verdict, not a fail section


def test_disclaimer_verbatim_in_all_formats() -> None:
    assessment = _assessment()
    assert DISCLAIMER in render_markdown(assessment)
    assert DISCLAIMER in render_html(assessment)
    # JSON carries content, not prose sections; certification wording ban still applies.
    assert "certif" not in render_json(assessment).replace(
        "It does not certify or guarantee compliance", ""
    )


def test_html_escapes_hostile_node_name() -> None:
    html = render_html(_assessment())
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_markdown_neutralizes_backticks_in_names() -> None:
    node = mk_node(node_id="tf:root:aws_db_instance.bt", name="a`b", encryption_at_rest=False)
    text = render_markdown(evaluate(mk_graph([node]), [mk_rule()]))
    assert "`ab`" in text


def test_include_passes_section() -> None:
    node = mk_node(encryption_at_rest=True)
    assessment = evaluate(mk_graph([node]), [mk_rule()])
    assert "## Passed checks" not in render_markdown(assessment)
    with_passes = render_markdown(assessment, include_passes=True)
    assert "## Passed checks" in with_passes and "TEST-SEC-001" in with_passes


def test_json_timestamp_flag() -> None:
    assessment = _assessment()
    plain = render_json(assessment)
    assert "generated_at" not in plain
    stamped = render_json(assessment, generated_at="2026-07-03T00:00:00+00:00")
    assert json.loads(stamped)["generated_at"] == "2026-07-03T00:00:00+00:00"


def test_renderers_are_deterministic() -> None:
    a1, a2 = _assessment(), _assessment()
    assert render_markdown(a1) == render_markdown(a2)
    assert render_html(a1) == render_html(a2)
    assert render_json(a1) == render_json(a2)


def test_empty_assessment_scores_100_with_disclaimer() -> None:
    assessment = evaluate(mk_graph([]), [mk_rule()])
    text = render_markdown(assessment)
    assert assessment.summary.score == 100
    assert "No failed checks." in text and DISCLAIMER in text
