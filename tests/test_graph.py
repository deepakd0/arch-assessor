"""Spec 001 acceptance tests: model, validation, canonical serialization."""

from __future__ import annotations

import pytest
from conftest import mk_graph, mk_node

from archassessor.graph.model import (
    EDGE_TYPES,
    NODE_TYPES,
    Edge,
    GraphValidationError,
    Node,
    SourceRef,
    from_json,
    to_json,
    validate,
)


def test_round_trip_all_types() -> None:
    nodes = [
        Node(
            id=f"tf:root:x.{t}",
            type=t,
            name=t,
            properties={"s": "text", "n": 7, "f": 1.5, "b": True, "nul": None, "l": ["a", "b"]},
            source=SourceRef(ingestor="test", file="a.tf", line=3),
        )
        for t in sorted(NODE_TYPES)
    ]
    ids = [n.id for n in nodes]
    edges = [Edge(from_id=ids[0], to_id=ids[1], type=t) for t in sorted(EDGE_TYPES)]
    graph = mk_graph(nodes, edges)
    text = to_json(graph)
    restored = from_json(text)
    assert to_json(restored) == text
    assert [n.id for n in sorted(restored.nodes, key=lambda n: n.id)] == sorted(ids)


def test_insertion_order_does_not_change_bytes() -> None:
    a, b, c = (mk_node(node_id=f"tf:root:aws_vpc.{i}", node_type="network") for i in "abc")
    e1 = Edge(from_id=a.id, to_id=b.id, type="contains")
    e2 = Edge(from_id=a.id, to_id=c.id, type="contains")
    texts = {
        to_json(mk_graph([a, b, c], [e1, e2])),
        to_json(mk_graph([c, a, b], [e2, e1])),
        to_json(mk_graph([b, c, a], [e1, e2])),
    }
    assert len(texts) == 1


def test_duplicate_edges_collapse() -> None:
    a = mk_node(node_id="tf:root:aws_vpc.a", node_type="network")
    b = mk_node(node_id="tf:root:aws_subnet.b", node_type="subnet")
    edge = Edge(from_id=a.id, to_id=b.id, type="contains")
    graph = mk_graph([a, b], [edge, Edge(from_id=a.id, to_id=b.id, type="contains")])
    assert len(graph.edges) == 1


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda g: setattr(g, "schema_version", "2.0"), "schema_version"),
        (lambda g: g.nodes.append(g.nodes[0]), "duplicate node id"),
        (lambda g: setattr(g.nodes[0], "type", "spaceship"), "unknown type"),
        (
            lambda g: g.edges.append(Edge(from_id=g.nodes[0].id, to_id="missing", type="contains")),
            "missing node",
        ),
        (
            lambda g: g.edges.append(
                Edge(from_id=g.nodes[0].id, to_id=g.nodes[0].id, type="contains")
            ),
            "self-loop",
        ),
        (lambda g: g.nodes[0].properties.update(bad={"nested": 1}), "unsupported value type"),
    ],
)
def test_validation_problems(mutate, fragment) -> None:
    graph = mk_graph([mk_node()])
    mutate(graph)
    problems = validate(graph)
    assert any(fragment in p for p in problems), problems


def test_multiple_problems_all_reported() -> None:
    graph = mk_graph([mk_node()])
    graph.nodes[0].type = "spaceship"
    graph.schema_version = "9.9"
    assert len(validate(graph)) == 2


def test_from_json_malformed_raises_graph_error() -> None:
    with pytest.raises(GraphValidationError) as exc:
        from_json("{not json")
    assert "not valid JSON" in str(exc.value)


def test_helper_queries_sorted_and_filtered() -> None:
    net = mk_node(node_id="tf:root:aws_vpc.v", node_type="network")
    s1 = mk_node(node_id="tf:root:aws_subnet.b", node_type="subnet")
    s2 = mk_node(node_id="tf:root:aws_subnet.a", node_type="subnet")
    graph = mk_graph(
        [net, s1, s2],
        [
            Edge(from_id=net.id, to_id=s1.id, type="contains"),
            Edge(from_id=net.id, to_id=s2.id, type="contains"),
        ],
    )
    assert [n.id for n in graph.nodes_of_type("subnet")] == [s2.id, s1.id]
    assert len(graph.edges_from(net.id, "contains")) == 2
    assert graph.edges_from(net.id, "depends_on") == []
    assert len(graph.edges_to(s1.id)) == 1
    assert graph.node_by_id("nope") is None
