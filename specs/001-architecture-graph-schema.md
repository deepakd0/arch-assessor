# Spec 001 — Architecture Graph Schema

**Depends on:** spec 000.
**Consumed by:** every other spec. This is the single most important interface in the product.

## 1. Purpose

Define the canonical, JSON-serializable model of an architecture: the **graph**. Every
ingestion source (Terraform now; documents, DSL, cloud APIs later) produces this structure,
and everything downstream (rules engine, reports, future diagrams) consumes it. It must be
expressive enough to describe real cloud architectures and boring enough that a beginner can
hold the whole schema in their head.

## 2. Scope

**In scope:** the JSON format; Python dataclasses mirroring it; serialization/deserialization;
structural validation; canonical (deterministic) serialization.

**Non-goals:** anything Terraform-specific (spec 002); rule evaluation (004); graph *merging*
from multiple sources (Phase 3+ — but the `source` field on every node exists so merging is
possible later without a schema break).

## 3. The JSON format

A graph is one JSON object:

```json
{
  "schema_version": "1.0",
  "metadata": {
    "ingestor": "terraform",
    "ingestor_version": "0.1.0",
    "source_root": "infra/"
  },
  "nodes": [
    {
      "id": "tf:root:aws_db_instance.main",
      "type": "database",
      "name": "main",
      "properties": {
        "engine": "postgres",
        "encryption_at_rest": true,
        "multi_az": false,
        "publicly_accessible": null
      },
      "source": {
        "ingestor": "terraform",
        "file": "infra/rds.tf",
        "line": 12
      }
    }
  ],
  "edges": [
    {
      "id": "tf:root:aws_db_instance.main--depends_on--tf:root:aws_security_group.db",
      "from": "tf:root:aws_db_instance.main",
      "to": "tf:root:aws_security_group.db",
      "type": "depends_on"
    }
  ]
}
```

### 3.1 Node fields

| Field | Type | Rules |
|-------|------|-------|
| `id` | string | Unique in the graph, stable across runs (same input → same id). Format is ingestor-defined; Terraform uses `tf:<module_path>:<resource_type>.<resource_name>` (see spec 002 §4). |
| `type` | string | One of the taxonomy values in §3.3. Unmappable elements use `unknown` — never invent new types. |
| `name` | string | Human-readable short name. |
| `properties` | object | Flat map of string → (string \| number \| boolean \| null \| list of strings). **`null` has a defined meaning: "we know this property is relevant but could not determine its value."** A property that is genuinely not applicable is simply absent. No nested objects — if you feel the need, you probably need another node. |
| `source` | object | `ingestor` (string, required), `file` (string, optional), `line` (integer ≥ 1, optional). |

### 3.2 Edge fields

| Field | Type | Rules |
|-------|------|-------|
| `id` | string | `"{from}--{type}--{to}"`. Derived, never hand-set. |
| `from`, `to` | string | Must reference existing node ids (validation enforces this). |
| `type` | string | One of §3.4. |

### 3.3 Node type taxonomy (v1.0 — closed set)

| Type | Meaning | Terraform examples (illustrative) |
|------|---------|-----------------------------------|
| `compute` | VM / instance | `aws_instance` |
| `container_service` | Container orchestration service/task | `aws_ecs_service` |
| `function` | Serverless function | `aws_lambda_function` |
| `database` | Relational/NoSQL database | `aws_db_instance`, `aws_dynamodb_table` |
| `cache` | In-memory cache | `aws_elasticache_cluster` |
| `storage` | Object/file storage | `aws_s3_bucket` |
| `queue` | Message queue | `aws_sqs_queue` |
| `topic` | Pub/sub topic | `aws_sns_topic` |
| `network` | VPC / virtual network | `aws_vpc` |
| `subnet` | Subnet | `aws_subnet` |
| `security_group` | Firewall / SG / NACL | `aws_security_group` |
| `load_balancer` | LB of any layer | `aws_lb` |
| `api_gateway` | Managed API front door | `aws_api_gateway_rest_api` |
| `dns_zone` | DNS zone | `aws_route53_zone` |
| `cdn` | CDN distribution | `aws_cloudfront_distribution` |
| `secret_store` | Secrets manager | `aws_secretsmanager_secret` |
| `kms_key` | Encryption key | `aws_kms_key` |
| `iam_role` | Identity/role/policy principal | `aws_iam_role` |
| `external_service` | Third-party dependency (declared, not scanned) | — |
| `unknown` | Recognized as a resource but unmappable | any unmapped resource |

Adding a type is a schema minor-version bump and requires updating this table, the validator,
and spec 002's mapping table.

### 3.4 Edge type taxonomy (v1.0 — closed set)

| Type | Meaning | Example |
|------|---------|---------|
| `contains` | Topological containment | network `contains` subnet; subnet `contains` compute |
| `depends_on` | Generic reference/dependency (default when nothing more specific applies) | function `depends_on` queue |
| `routes_to` | Traffic forwarding | load_balancer `routes_to` compute |

### 3.5 Canonical property names

Rules (spec 003) match on property names, so ingestors must normalize to these names — never
provider-specific ones (`storage_encrypted` → `encryption_at_rest`). Booleans below are
tri-state: `true` / `false` / `null` (undeterminable).

- **All types:** `region` (string), `tags` (list of `"key=value"` strings, sorted).
- **database:** `engine`, `encryption_at_rest`, `multi_az`, `publicly_accessible`,
  `backup_retention_days` (number), `deletion_protection`.
- **storage:** `encryption_at_rest`, `versioning_enabled`, `public_access_blocked`,
  `logging_enabled`.
- **compute:** `public_ip` (bool), `instance_type` (string).
- **security_group:** `open_to_world` (bool — any 0.0.0.0/0 or ::/0 ingress),
  `open_to_world_ports` (list of strings, e.g. `["22", "443"]`).
- **load_balancer:** `internal` (bool), `scheme` (string).
- **queue / topic:** `encryption_at_rest`.
- **function:** `runtime` (string).
- **kms_key:** `rotation_enabled` (bool).

This list will grow; growth is additive (minor version).

## 4. Python API (module `archassessor.graph`)

```python
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
    properties: dict[str, PropertyValue]   # PropertyValue = str|int|float|bool|None|list[str]
    source: SourceRef

@dataclass
class Edge:
    from_id: str      # serialized as "from"
    to_id: str        # serialized as "to"
    type: str
    @property
    def id(self) -> str: ...  # "{from}--{type}--{to}"

@dataclass
class Graph:
    metadata: dict[str, str]
    nodes: list[Node]
    edges: list[Edge]
    schema_version: str = "1.0"

    def node_by_id(self, node_id: str) -> Node | None: ...
    def nodes_of_type(self, node_type: str) -> list[Node]: ...          # sorted by id
    def edges_from(self, node_id: str, edge_type: str | None = None) -> list[Edge]: ...
    def edges_to(self, node_id: str, edge_type: str | None = None) -> list[Edge]: ...

def to_json(graph: Graph) -> str:
    """Canonical serialization: keys sorted, nodes sorted by id, edges by id,
    2-space indent, ensure_ascii=False, trailing newline."""

def from_json(text: str) -> Graph:
    """Parse and validate; raises GraphValidationError with all problems listed."""

def validate(graph: Graph) -> list[str]:
    """Return human-readable problem strings; empty list = valid."""
```

### Validation checks (each produces a distinct message)

1. `schema_version` major is `1`.
2. Node ids unique; node `type` in §3.3; edge `type` in §3.4.
3. Every edge endpoint references an existing node id.
4. Property values are only the allowed scalar/list types (no nested objects).
5. `source.ingestor` non-empty; `line`, if present, ≥ 1.

## 5. Edge cases

- **Empty graph** (no nodes, no edges) is valid — parsers may produce it for an empty directory.
- **Duplicate edges** (same from/type/to) are collapsed to one during construction.
- **Self-loops** (`from == to`) are invalid — reject in validation.
- **Round-trip:** `from_json(to_json(g))` must produce an equal graph, and
  `to_json(from_json(text))` must be byte-identical for canonical input.

## 6. Acceptance criteria (write these as pytest tests)

1. Construct the example graph from §3 in Python, serialize, and match the expected JSON
   byte-for-byte (fixture file).
2. Round-trip property: build a graph with every node type, every edge type, every property
   value kind (incl. `null` and lists) → `to_json` → `from_json` → equal.
3. Deterministic ordering: build the same graph with nodes/edges inserted in three different
   orders → identical `to_json` output.
4. Validation: each of the five checks above has a test with a bad graph producing the right
   message; a graph with two problems reports both.
5. `from_json` on malformed JSON raises `GraphValidationError` (not `json.JSONDecodeError`)
   with a message a non-programmer could act on.
6. Helper queries (`nodes_of_type`, `edges_from`, `edges_to`) return sorted, filtered results.
