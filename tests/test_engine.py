"""Spec 004 acceptance tests: truth tables, Kleene logic, score, rollup, purity."""

from __future__ import annotations

import pytest
from conftest import mk_graph, mk_node, mk_rule

from archassessor.engine.conditions import evaluate_condition
from archassessor.engine.evaluate import Finding, assessment_to_json, evaluate
from archassessor.graph.model import Edge, SourceRef
from archassessor.rules.schema import Combinator, Leaf, Related

G = mk_graph([])  # leaf evaluation ignores the graph


def _leaf(prop: str, op: str, operand: object) -> Leaf:
    return Leaf(property=prop, operator=op, operand=operand)


# --- §5.1 truth tables: satisfying / violating / missing per operator ---------

CASES = [
    ("equals", True, {"p": True}, "pass"),
    ("equals", True, {"p": False}, "fail"),
    ("equals", True, {}, "unknown"),
    ("equals", 1, {"p": "1"}, "fail"),  # type-sensitive
    ("not_equals", True, {"p": False}, "pass"),
    ("not_equals", True, {"p": True}, "fail"),
    ("not_equals", True, {"p": None}, "unknown"),
    ("exists", True, {"p": "x"}, "pass"),
    ("exists", True, {}, "fail"),
    ("exists", False, {}, "pass"),
    ("exists", False, {"p": 1}, "fail"),
    ("in", ["a", "b"], {"p": "a"}, "pass"),
    ("in", ["a", "b"], {"p": "z"}, "fail"),
    ("in", ["a", "b"], {}, "unknown"),
    ("not_in", ["a"], {"p": "z"}, "pass"),
    ("gte", 7, {"p": 9}, "pass"),
    ("gte", 7, {"p": 3}, "fail"),
    ("gte", 7, {"p": "many"}, "fail"),  # non-numeric -> fail with type detail
    ("gte", 7, {}, "unknown"),
    ("lte", 7, {"p": 7}, "pass"),
    ("contains", "22", {"p": ["22", "80"]}, "pass"),
    ("contains", "22", {"p": []}, "fail"),
    ("contains", "22", {"p": "22"}, "fail"),  # not a list
    ("contains", "22", {}, "unknown"),
    ("not_contains", "22", {"p": ["80"]}, "pass"),
    ("not_contains", "22", {"p": ["22"]}, "fail"),
    ("matches", "post.*", {"p": "postgres"}, "pass"),
    ("matches", "post.*", {"p": "mysql"}, "fail"),
    ("matches", "post.*", {"p": 5}, "fail"),
    ("matches", "post.*", {}, "unknown"),
]


@pytest.mark.parametrize(("op", "operand", "props", "expected"), CASES)
def test_leaf_truth_tables(op: str, operand: object, props: dict, expected: str) -> None:
    node = mk_node(**props)
    verdict, detail = evaluate_condition(node, G, _leaf("p", op, operand))
    assert verdict == expected
    assert detail  # every verdict carries a deterministic explanation


def test_unknown_detail_wording() -> None:
    node = mk_node()
    _, detail = evaluate_condition(node, G, _leaf("publicly_accessible", "equals", True))
    assert detail == "`publicly_accessible` could not be determined from the source"


def test_has_tag_key() -> None:
    tagged = mk_node(tags=["environment=prod", "owner=core"])
    untagged = mk_node(tags=[])
    cond = Leaf(property="tags", operator="has_tag_key", operand="owner")
    assert evaluate_condition(tagged, G, cond)[0] == "pass"
    assert evaluate_condition(untagged, G, cond)[0] == "fail"


# --- §5.2 Kleene combinators ---------------------------------------------------

P = _leaf("p_pass", "equals", True)
F = _leaf("p_fail", "equals", True)
U = _leaf("p_unknown", "equals", True)
KLEENE_NODE = mk_node(p_pass=True, p_fail=False)  # p_unknown absent


@pytest.mark.parametrize(
    ("kind", "children", "expected"),
    [
        ("all", [P, P], "pass"),
        ("all", [P, F], "fail"),
        ("all", [P, U], "unknown"),
        ("all", [F, U], "fail"),
        ("any", [P, F], "pass"),
        ("any", [F, F], "fail"),
        ("any", [F, U], "unknown"),
        ("any", [P, U], "pass"),
        ("none", [F, F], "pass"),
        ("none", [P, F], "fail"),
        ("none", [F, U], "unknown"),
    ],
)
def test_kleene(kind: str, children: list[Leaf], expected: str) -> None:
    verdict, _ = evaluate_condition(KLEENE_NODE, G, Combinator(kind=kind, children=children))
    assert verdict == expected


# --- §5.3 related ---------------------------------------------------------------


def _related_graph():
    db = mk_node(node_id="tf:root:aws_db_instance.a", node_type="database")
    key = mk_node(node_id="tf:root:aws_kms_key.k", node_type="kms_key")
    subnet = mk_node(node_id="tf:root:aws_subnet.s", node_type="subnet")
    graph = mk_graph(
        [db, key, subnet],
        [
            Edge(from_id=db.id, to_id=key.id, type="depends_on"),
            Edge(from_id=subnet.id, to_id=db.id, type="contains"),
        ],
    )
    return graph, db


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"edge_type": "depends_on", "target_type": "kms_key"}, "pass"),
        ({"edge_type": "depends_on", "target_type": "queue"}, "fail"),
        ({"edge_type": "routes_to"}, "fail"),
        ({"edge_type": "contains", "direction": "incoming", "target_type": "subnet"}, "pass"),
        ({"edge_type": "depends_on", "exists": False}, "fail"),
        ({"edge_type": "routes_to", "exists": False}, "pass"),
    ],
)
def test_related(kwargs: dict, expected: str) -> None:
    graph, db = _related_graph()
    verdict, _ = evaluate_condition(db, graph, Related(**kwargs))
    assert verdict == expected


# --- §4 subjects, §5.5 score, §7 rollup ------------------------------------------


def test_where_filter_excludes_fail_and_unknown() -> None:
    pg = mk_node(node_id="tf:root:aws_db_instance.pg", engine="postgres", encryption_at_rest=True)
    dynamo = mk_node(
        node_id="tf:root:aws_db_instance.dy", engine="dynamodb", encryption_at_rest=True
    )
    unknown_engine = mk_node(node_id="tf:root:aws_db_instance.uk", encryption_at_rest=True)
    rule = mk_rule(where=_leaf("engine", "not_equals", "dynamodb"))
    assessment = evaluate(mk_graph([pg, dynamo, unknown_engine]), [rule])
    assert [r.node_id for r in assessment.results] == [pg.id]


def test_not_applicable_and_rollup_not_assessed() -> None:
    rule = mk_rule(node_type="cdn", mappings={"soc2": ["CC9.9"]})
    assessment = evaluate(mk_graph([mk_node()]), [rule])
    assert assessment.not_applicable_rule_ids == [rule.id]
    assert assessment.frameworks[0].status == "not_assessed"


def test_score_formula_spec_example() -> None:
    # 1 critical fail + 1 high unknown + 2 medium fails -> 100-15-5-10 = 70
    nodes = [
        mk_node(
            node_id="tf:root:aws_s3_bucket.a", node_type="storage", public_access_blocked=False
        ),
        mk_node(node_id="tf:root:aws_db_instance.b", encryption_at_rest=None),
        mk_node(node_id="tf:root:aws_kms_key.c", node_type="kms_key", rotation_enabled=False),
        mk_node(node_id="tf:root:aws_sqs_queue.d", node_type="queue", encryption_at_rest=False),
    ]
    rules = [
        mk_rule(
            "TEST-AAA-001", "storage", _leaf("public_access_blocked", "equals", True), "critical"
        ),
        mk_rule("TEST-BBB-002", "database", _leaf("encryption_at_rest", "equals", True), "high"),
        mk_rule("TEST-CCC-003", "kms_key", _leaf("rotation_enabled", "equals", True), "medium"),
        mk_rule("TEST-DDD-004", "queue", _leaf("encryption_at_rest", "equals", True), "medium"),
    ]
    assessment = evaluate(mk_graph(nodes), rules)
    assert assessment.summary.score == 70


@pytest.mark.parametrize(
    ("db_value", "expected_status"),
    [(True, "satisfied"), (False, "gap"), (None, "unknown")],
)
def test_rollup_statuses(db_value: bool | None, expected_status: str) -> None:
    node = mk_node(encryption_at_rest=db_value)
    rule = mk_rule(mappings={"soc2": ["CC6.1"]})
    assessment = evaluate(mk_graph([node]), [rule])
    status = assessment.frameworks[0]
    assert (status.framework, status.control) == ("soc2", "CC6.1")
    assert status.status == expected_status


def test_rollup_gap_beats_unknown_across_rules() -> None:
    node = mk_node(encryption_at_rest=None, multi_az=False)
    rule_a = mk_rule(
        "TEST-AAA-001",
        condition=_leaf("encryption_at_rest", "equals", True),
        mappings={"soc2": ["CC6.1"]},
    )
    rule_b = mk_rule(
        "TEST-BBB-001", condition=_leaf("multi_az", "equals", True), mappings={"soc2": ["CC6.1"]}
    )
    assessment = evaluate(mk_graph([node]), [rule_a, rule_b])
    assert assessment.frameworks[0].status == "gap"
    assert assessment.frameworks[0].rule_ids == ["TEST-AAA-001", "TEST-BBB-001"]


def test_determinism_and_purity() -> None:
    nodes = [
        mk_node(node_id=f"tf:root:aws_db_instance.{i}", encryption_at_rest=False) for i in "cab"
    ]
    rules = [mk_rule(f"TEST-SEC-00{i}") for i in (3, 1, 2)]
    graph1 = mk_graph(list(nodes))
    graph2 = mk_graph(list(reversed(nodes)))
    before = assessment_to_json(evaluate(graph1, rules))
    again = assessment_to_json(evaluate(graph2, list(reversed(rules))))
    assert before == again
    # purity: same objects evaluated twice, inputs not mutated
    snapshot = [dict(n.properties) for n in nodes]
    evaluate(graph1, rules)
    assert [dict(n.properties) for n in nodes] == snapshot


def test_external_findings_join_everything() -> None:
    external = Finding(
        rule_id="TRIVY-CVE-001",
        rule_title="Critical CVE on payments service",
        severity="critical",
        category="security",
        description="imported scanner finding",
        node_id="tf:root:aws_instance.pay",
        node_name="pay",
        node_type="compute",
        verdict="fail",
        detail="CVE-2026-0001 (from SARIF import)",
        remediation="Upgrade the base image.",
        mappings={"soc2": ["CC7.1"]},
        source=SourceRef(ingestor="sarif"),
    )
    assessment = evaluate(mk_graph([]), [], external_findings=(external,))
    assert assessment.findings == [external]
    assert assessment.summary.findings_by_severity["critical"] == 1
    assert assessment.summary.score == 85
    assert assessment.frameworks[0].status == "gap"
