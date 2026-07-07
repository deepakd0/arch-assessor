"""Property-based invariants (spec 009 §3): hold for *generated* inputs, not
just hand-picked ones. These are the guarantees the product sells.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from archassessor.engine.evaluate import assessment_to_json, evaluate
from archassessor.graph.model import (
    EDGE_TYPES,
    NODE_TYPES,
    Edge,
    Graph,
    Node,
    SourceRef,
    from_json,
    to_json,
)
from archassessor.rules.schema import Combinator, Leaf, Match, Rule

# --- strategies -----------------------------------------------------------------

property_values = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**9), max_value=10**9),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    st.text(max_size=20),
    st.lists(st.text(max_size=10), max_size=4),
)

prop_names = st.text(alphabet="abcdefgh_", min_size=1, max_size=8)


@st.composite
def graphs(draw: st.DrawFn) -> Graph:
    ids = sorted(draw(st.sets(st.integers(0, 99), max_size=8)))
    node_ids = [f"tf:root:aws_thing.n{i:02d}" for i in ids]
    nodes = [
        Node(
            id=node_id,
            type=draw(st.sampled_from(sorted(NODE_TYPES))),
            name=node_id.rsplit(".", 1)[-1],
            properties=draw(st.dictionaries(prop_names, property_values, max_size=4)),
            source=SourceRef(ingestor="gen", file="gen.tf", line=1),
        )
        for node_id in node_ids
    ]
    edges: list[Edge] = []
    if len(node_ids) >= 2:
        for _ in range(draw(st.integers(0, 6))):
            a = draw(st.sampled_from(node_ids))
            b = draw(st.sampled_from(node_ids))
            if a != b:
                edges.append(
                    Edge(from_id=a, to_id=b, type=draw(st.sampled_from(sorted(EDGE_TYPES))))
                )
    return Graph(metadata={"ingestor": "gen", "source_root": "gen"}, nodes=nodes, edges=edges)


leaf_conditions = st.one_of(
    st.builds(
        Leaf,
        property=prop_names,
        operator=st.just("equals"),
        operand=st.one_of(st.booleans(), st.integers(0, 9), st.text(max_size=5)),
    ),
    st.builds(Leaf, property=prop_names, operator=st.just("exists"), operand=st.booleans()),
    st.builds(Leaf, property=prop_names, operator=st.just("gte"), operand=st.integers(0, 100)),
    st.builds(Leaf, property=prop_names, operator=st.just("contains"), operand=st.text(max_size=5)),
    st.builds(
        Leaf,
        property=st.just("tags"),
        operator=st.just("has_tag_key"),
        operand=st.text(alphabet="abc", min_size=1, max_size=3),
    ),
)

conditions = st.recursive(
    leaf_conditions,
    lambda children: st.builds(
        Combinator,
        kind=st.sampled_from(["all", "any", "none"]),
        children=st.lists(children, min_size=1, max_size=3),
    ),
    max_leaves=6,
)


# --- invariants -------------------------------------------------------------------


@settings(max_examples=60, deadline=None)
@given(graph=graphs())
def test_canonical_serialization_is_stable(graph: Graph) -> None:
    text = to_json(graph)
    assert to_json(from_json(text)) == text


@settings(max_examples=40, deadline=None)
@given(graph=graphs(), seed=st.randoms(use_true_random=False))
def test_insertion_order_never_changes_bytes(graph: Graph, seed) -> None:
    shuffled_nodes = list(graph.nodes)
    shuffled_edges = list(graph.edges)
    seed.shuffle(shuffled_nodes)
    seed.shuffle(shuffled_edges)
    reordered = Graph(metadata=dict(graph.metadata), nodes=shuffled_nodes, edges=shuffled_edges)
    assert to_json(reordered) == to_json(graph)


@settings(max_examples=60, deadline=None)
@given(graph=graphs(), condition=conditions)
def test_engine_is_total_and_deterministic(graph: Graph, condition) -> None:
    rule = Rule(
        id="GEN-SEC-001",
        title="generated",
        severity="high",
        category="security",
        description="generated",
        remediation="generated",
        mappings={"soc2": ["CC6.1"]},
        match=Match(node_types=["any"]),
        condition=condition,
        source_file="gen",
    )
    assessment = evaluate(graph, [rule])  # must never raise
    assert 0 <= assessment.summary.score <= 100
    assert all(r.verdict in {"pass", "fail", "unknown"} for r in assessment.results)
    assert all(r.detail for r in assessment.results)
    # determinism: same inputs -> identical bytes
    assert assessment_to_json(evaluate(graph, [rule])) == assessment_to_json(assessment)
    # purity: verdict counts reconcile
    s = assessment.summary
    assert s.results_pass + s.results_fail + s.results_unknown == len(assessment.results)
