"""Abuse suite (spec 009 §4): one test per threat-model mitigation (spec 008)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from conftest import mk_node

from archassessor.engine.conditions import MAX_MATCHED_STRING, evaluate_condition
from archassessor.graph.model import GraphValidationError, from_json
from archassessor.ingest.terraform.parser import MAX_FILE_BYTES, parse_directory
from archassessor.rules.schema import Leaf

SRC = Path(__file__).parent.parent / "src"


def test_t1_oversized_file_skipped_with_w007(tmp_path: Path) -> None:
    big = tmp_path / "big.tf"
    with big.open("w") as handle:
        handle.write("# padding\n" * (MAX_FILE_BYTES // 10 + 1))
    (tmp_path / "ok.tf").write_text('resource "aws_vpc" "v" {}\n')

    started = time.monotonic()
    result = parse_directory(tmp_path)
    assert time.monotonic() - started < 5  # skipped, not parsed

    assert [w.code for w in result.warnings if w.code == "W007"] == ["W007"]
    assert result.graph.node_by_id("tf:root:aws_vpc.v") is not None
    assert result.graph.node_by_id("tf:root:aws_vpc.big") is None


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ on Windows")
def test_t4_symlink_escape_skipped_with_w008(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.tf"
    secret.write_text('resource "aws_vpc" "outside_repo" {}\n')

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ok.tf").write_text('resource "aws_vpc" "inside" {}\n')
    (repo / "sneaky.tf").symlink_to(secret)

    result = parse_directory(repo)
    assert any(w.code == "W008" and w.file == "sneaky.tf" for w in result.warnings)
    assert result.graph.node_by_id("tf:root:aws_vpc.inside") is not None
    assert result.graph.node_by_id("tf:root:aws_vpc.outside_repo") is None


def test_t3_catastrophic_regex_is_time_bounded() -> None:
    # (a+)+$ against a long non-matching subject is the classic ReDoS shape.
    # The subject-length cap must kick in before the regex engine ever runs.
    node = mk_node(p="a" * (MAX_MATCHED_STRING + 1) + "b")
    cond = Leaf(property="p", operator="matches", operand="(a+)+$")
    started = time.monotonic()
    verdict, detail = evaluate_condition(node, None, cond)  # type: ignore[arg-type]
    assert time.monotonic() - started < 1.0
    assert verdict == "unknown"
    assert "too long" in detail


def test_t3_regex_at_cap_still_evaluates() -> None:
    node = mk_node(p="a" * 100)
    cond = Leaf(property="p", operator="matches", operand="a+")
    assert evaluate_condition(node, None, cond)[0] == "pass"  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "payload",
    [
        '{"schema_version": "1.0", "metadata": {}, "nodes": [{"id": "a", "type": "compute",'
        ' "name": "a", "properties": {}, "source": {"ingestor": "x", "line": "NaN"}}], "edges": []}',
        '{"schema_version": "1.0", "metadata": {}, "nodes": [{"id": "a", "type": "compute",'
        ' "name": "a", "properties": {}, "source": {"ingestor": "x", "file": 42}}], "edges": []}',
        '{"schema_version": "1.0", "metadata": {"k": 1}, "nodes": [], "edges": []}',
        '{"schema_version": "1.0", "metadata": {}, "nodes": [{"id": "a", "type": "compute",'
        ' "name": "a", "properties": {"p": {"nested": 1}}, "source": {"ingestor": "x"}}], "edges": []}',
        '["not", "an", "object"]',
    ],
)
def test_hostile_graph_json_never_crashes(payload: str) -> None:
    # Every malformed document must become a GraphValidationError with readable
    # problems — never a TypeError/KeyError escaping to the caller.
    with pytest.raises(GraphValidationError) as exc:
        from_json(payload)
    assert exc.value.problems


def test_t2_no_unsafe_yaml_load_in_source() -> None:
    # Mirror of the CI grep gate: yaml.load( must never appear (safe_load only).
    offenders = [
        path for path in SRC.rglob("*.py") if "yaml.load(" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_engine_scales_linearly_on_related_rules() -> None:
    # NFR-P5 guard: 2,000 compute nodes in subnets through a `related` rule.
    # Pre-index this was O(nodes x edges); indexed it must finish fast.
    from conftest import mk_graph, mk_rule

    from archassessor.engine.evaluate import evaluate
    from archassessor.graph.model import Edge
    from archassessor.rules.schema import Related

    nodes, edges = [], []
    for i in range(2000):
        subnet = mk_node(node_id=f"tf:root:aws_subnet.s{i:04d}", node_type="subnet")
        box = mk_node(node_id=f"tf:root:aws_instance.c{i:04d}", node_type="compute")
        nodes += [subnet, box]
        edges.append(Edge(from_id=subnet.id, to_id=box.id, type="contains"))
    rule = mk_rule(
        "TEST-NET-001",
        "compute",
        Related(edge_type="contains", direction="incoming", target_type="subnet"),
    )
    started = time.monotonic()
    assessment = evaluate(mk_graph(nodes, edges), [rule])
    assert time.monotonic() - started < 3.0
    assert assessment.summary.results_pass == 2000
