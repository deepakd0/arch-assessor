"""Graph data model, validation, and canonical JSON serialization (spec 001).

Canonical form: keys sorted, nodes sorted by id, edges sorted by id,
2-space indent, ensure_ascii=False, trailing newline. Same graph always
serializes to identical bytes (spec 000 §4).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

SCHEMA_VERSION = "1.0"

PropertyValue = str | int | float | bool | None | list[str]

NODE_TYPES: frozenset[str] = frozenset(
    {
        "compute",
        "container_service",
        "function",
        "database",
        "cache",
        "storage",
        "queue",
        "topic",
        "network",
        "subnet",
        "security_group",
        "load_balancer",
        "api_gateway",
        "dns_zone",
        "cdn",
        "secret_store",
        "kms_key",
        "iam_role",
        "external_service",
        "unknown",
    }
)

EDGE_TYPES: frozenset[str] = frozenset({"contains", "depends_on", "routes_to"})


class GraphValidationError(Exception):
    """Raised when a graph fails structural validation; lists every problem."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("invalid graph: " + "; ".join(problems))


@dataclass(frozen=True)
class SourceRef:
    ingestor: str
    file: str | None = None
    line: int | None = None


@dataclass
class Node:
    id: str
    type: str
    name: str
    properties: dict[str, PropertyValue]
    source: SourceRef


@dataclass
class Edge:
    from_id: str
    to_id: str
    type: str

    @property
    def id(self) -> str:
        return f"{self.from_id}--{self.type}--{self.to_id}"


@dataclass
class Graph:
    metadata: dict[str, str]
    nodes: list[Node]
    edges: list[Edge]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        seen: set[str] = set()
        unique: list[Edge] = []
        for edge in self.edges:
            if edge.id not in seen:
                seen.add(edge.id)
                unique.append(edge)
        self.edges = unique

    def node_by_id(self, node_id: str) -> Node | None:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def nodes_of_type(self, node_type: str) -> list[Node]:
        return sorted((n for n in self.nodes if n.type == node_type), key=lambda n: n.id)

    def edges_from(self, node_id: str, edge_type: str | None = None) -> list[Edge]:
        found = (
            e
            for e in self.edges
            if e.from_id == node_id and (edge_type is None or e.type == edge_type)
        )
        return sorted(found, key=lambda e: e.id)

    def edges_to(self, node_id: str, edge_type: str | None = None) -> list[Edge]:
        found = (
            e
            for e in self.edges
            if e.to_id == node_id and (edge_type is None or e.type == edge_type)
        )
        return sorted(found, key=lambda e: e.id)


_ALLOWED_SCALARS = (str, int, float, bool)


def _valid_property(value: object) -> bool:
    if value is None or isinstance(value, _ALLOWED_SCALARS):
        return True
    if isinstance(value, list):
        return all(isinstance(item, str) for item in value)
    return False


def validate(graph: Graph) -> list[str]:
    """Return human-readable problem strings; empty list means valid."""
    problems: list[str] = []

    major = graph.schema_version.split(".", 1)[0]
    if major != "1":
        problems.append(
            f"unsupported schema_version {graph.schema_version!r} (this tool reads major version 1)"
        )

    seen_ids: set[str] = set()
    for node in graph.nodes:
        if node.id in seen_ids:
            problems.append(f"duplicate node id {node.id!r}")
        seen_ids.add(node.id)
        if node.type not in NODE_TYPES:
            problems.append(f"node {node.id!r} has unknown type {node.type!r}")
        for key, value in node.properties.items():
            if not _valid_property(value):
                problems.append(
                    f"node {node.id!r} property {key!r} has unsupported value type "
                    f"{type(value).__name__} (allowed: string, number, boolean, null, list of strings)"
                )
        if not node.source.ingestor:
            problems.append(f"node {node.id!r} source.ingestor must be non-empty")
        if node.source.line is not None and node.source.line < 1:
            problems.append(f"node {node.id!r} source.line must be >= 1")

    node_ids = {n.id for n in graph.nodes}
    for edge in graph.edges:
        if edge.type not in EDGE_TYPES:
            problems.append(f"edge {edge.id!r} has unknown type {edge.type!r}")
        if edge.from_id == edge.to_id:
            problems.append(f"edge {edge.id!r} is a self-loop, which is not allowed")
        for endpoint in (edge.from_id, edge.to_id):
            if endpoint not in node_ids:
                problems.append(f"edge {edge.id!r} references missing node {endpoint!r}")

    for key, value in graph.metadata.items():
        if not isinstance(value, str):
            problems.append(f"metadata {key!r} must be a string")

    return problems


def _node_payload(node: Node) -> dict[str, object]:
    source: dict[str, object] = {"ingestor": node.source.ingestor}
    if node.source.file is not None:
        source["file"] = node.source.file
    if node.source.line is not None:
        source["line"] = node.source.line
    return {
        "id": node.id,
        "type": node.type,
        "name": node.name,
        "properties": node.properties,
        "source": source,
    }


def to_json(graph: Graph) -> str:
    """Serialize to canonical JSON (byte-deterministic for equal graphs)."""
    payload = {
        "schema_version": graph.schema_version,
        "metadata": graph.metadata,
        "nodes": [_node_payload(n) for n in sorted(graph.nodes, key=lambda n: n.id)],
        "edges": [
            {"id": e.id, "from": e.from_id, "to": e.to_id, "type": e.type}
            for e in sorted(graph.edges, key=lambda e: e.id)
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def from_json(text: str) -> Graph:
    """Parse and validate a graph document; raises GraphValidationError on any problem."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GraphValidationError(
            [f"not valid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"]
        ) from exc
    if not isinstance(raw, dict):
        raise GraphValidationError(["top level must be a JSON object"])

    problems: list[str] = []
    nodes: list[Node] = []
    for i, item in enumerate(raw.get("nodes", [])):
        if not isinstance(item, dict):
            problems.append(f"nodes[{i}] must be an object")
            continue
        source_raw = item.get("source", {})
        if not isinstance(source_raw, dict):
            problems.append(f"nodes[{i}].source must be an object")
            source_raw = {}
        try:
            nodes.append(
                Node(
                    id=str(item.get("id", "")),
                    type=str(item.get("type", "")),
                    name=str(item.get("name", "")),
                    properties=dict(item.get("properties", {})),
                    source=SourceRef(
                        ingestor=str(source_raw.get("ingestor", "")),
                        file=source_raw.get("file"),
                        line=source_raw.get("line"),
                    ),
                )
            )
        except (TypeError, ValueError) as exc:
            problems.append(f"nodes[{i}] is malformed: {exc}")

    edges: list[Edge] = []
    for i, item in enumerate(raw.get("edges", [])):
        if not isinstance(item, dict):
            problems.append(f"edges[{i}] must be an object")
            continue
        edges.append(
            Edge(
                from_id=str(item.get("from", "")),
                to_id=str(item.get("to", "")),
                type=str(item.get("type", "")),
            )
        )

    metadata_raw = raw.get("metadata", {})
    graph = Graph(
        metadata=dict(metadata_raw) if isinstance(metadata_raw, dict) else {},
        nodes=nodes,
        edges=edges,
        schema_version=str(raw.get("schema_version", "")),
    )
    problems.extend(validate(graph))
    if problems:
        raise GraphValidationError(problems)
    return graph
