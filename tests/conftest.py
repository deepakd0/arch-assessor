"""Shared test helpers: quick graph/rule builders and fixture paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from archassessor.graph.model import Edge, Graph, Node, PropertyValue, SourceRef
from archassessor.rules.schema import Condition, Match, Rule

FIXTURES = Path(__file__).parent / "fixtures"
TF = FIXTURES / "terraform"


def mk_node(
    node_id: str = "tf:root:aws_db_instance.main",
    node_type: str = "database",
    name: str = "main",
    file: str | None = "main.tf",
    **props: PropertyValue,
) -> Node:
    return Node(
        id=node_id,
        type=node_type,
        name=name,
        properties=dict(props),
        source=SourceRef(ingestor="test", file=file, line=1 if file else None),
    )


def mk_graph(nodes: list[Node], edges: list[Edge] | None = None) -> Graph:
    return Graph(
        metadata={"ingestor": "test", "source_root": "fixture"}, nodes=nodes, edges=edges or []
    )


def mk_rule(
    rule_id: str = "TEST-SEC-001",
    node_type: str | list[str] = "database",
    condition: Condition | None = None,
    severity: str = "high",
    mappings: dict[str, list[str]] | None = None,
    where: Condition | None = None,
) -> Rule:
    from archassessor.rules.schema import Leaf

    node_types = node_type if isinstance(node_type, list) else [node_type]
    return Rule(
        id=rule_id,
        title=f"Test rule {rule_id}",
        severity=severity,
        category="security",
        description="test description",
        remediation="test remediation",
        mappings=mappings or {},
        match=Match(node_types=node_types, where=where),
        condition=condition or Leaf(property="encryption_at_rest", operator="equals", operand=True),
        source_file="test",
    )


@pytest.fixture()
def db_node() -> Node:
    return mk_node(encryption_at_rest=True, multi_az=False)
