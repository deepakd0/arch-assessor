# Spec 002 — Terraform Parser (IaC Ingestor)

**Depends on:** specs 000, 001.
**Consumed by:** the CLI (006). Output is a spec-001 graph.

## 1. Purpose

Convert a directory of Terraform HCL files into an architecture graph — offline, with no
credentials, no `terraform` binary, and no network access. This is the first ingestor and
the CLI's default input path.

## 2. Scope

**In scope:** parsing `*.tf` files with the `python-hcl2` library (pin the latest release in
`requirements.txt`); mapping AWS resources to graph nodes; extracting edges from references;
resolving simple variables and locals; local modules; deterministic output; a warnings channel.

**Non-goals (document, don't build):** other providers (Azure/GCP → Phase 2 backlog);
remote/registry modules (emit a warning, skip); evaluating arbitrary HCL expressions
(conditionals, `for` expressions, function calls — unresolvable values become `null`);
`terraform.tfstate` or plan JSON (a future, separate ingestor); `count`/`for_each` expansion
(v1 treats the resource as a single node; emit warning `W005`).

## 3. Public API (module `archassessor.ingest.terraform`)

```python
@dataclass
class ParseResult:
    graph: Graph
    warnings: list[Warning_]   # dataclass: code, message, file, line

def parse_directory(root: Path) -> ParseResult:
    """Parse all *.tf files under root (recursive, skipping .terraform/ dirs).

    Never raises on malformed user input: file-level HCL syntax errors become
    W001 warnings and that file is skipped. Raises only on our own bugs.
    """
```

Warning codes: `W001` unparseable file, `W002` unresolvable reference target,
`W003` remote module skipped, `W004` unmapped resource type (node still emitted as
`unknown`), `W005` count/for_each not expanded, `W006` unresolvable expression (property
set to `null`).

## 4. Node identity

`tf:<module_path>:<resource_type>.<resource_name>`

- Root module: `module_path` = `root` → `tf:root:aws_db_instance.main`.
- Local module call `module "networking"`: `tf:root.networking:aws_vpc.main`; nested calls
  join with dots. Same input always yields the same id (this is what makes assessments
  diffable over time).

## 5. Resource mapping

`mappings.py` holds one declarative table: Terraform resource type → (node type, property
extractors). Keep it data, not code, so adding resources is a one-line change.

### 5.1 v1 resource coverage (all must be implemented)

| Terraform type | Node type | Extracted properties (canonical names, spec 001 §3.5) |
|---|---|---|
| `aws_instance` | `compute` | `instance_type`; `public_ip` from `associate_public_ip_address` |
| `aws_ecs_service` | `container_service` | — |
| `aws_lambda_function` | `function` | `runtime` |
| `aws_db_instance` | `database` | `engine`; `encryption_at_rest` ← `storage_encrypted`; `multi_az`; `publicly_accessible`; `backup_retention_days` ← `backup_retention_period`; `deletion_protection` |
| `aws_rds_cluster` | `database` | `engine`; `encryption_at_rest` ← `storage_encrypted`; `deletion_protection`; `backup_retention_days` ← `backup_retention_period` |
| `aws_dynamodb_table` | `database` | `engine` = `"dynamodb"`; `encryption_at_rest` ← `server_side_encryption.enabled` (absent block → `true`, AWS default) |
| `aws_elasticache_cluster` | `cache` | `engine` |
| `aws_s3_bucket` | `storage` | `versioning_enabled` ← legacy inline `versioning.enabled`; else `null` |
| `aws_s3_bucket_server_side_encryption_configuration` | *(modifier — see §5.2)* | sets `encryption_at_rest: true` on the referenced bucket |
| `aws_s3_bucket_public_access_block` | *(modifier)* | sets `public_access_blocked` = AND of its four booleans |
| `aws_s3_bucket_versioning` | *(modifier)* | sets `versioning_enabled` ← `versioning_configuration.status == "Enabled"` |
| `aws_sqs_queue` | `queue` | `encryption_at_rest` ← (`sqs_managed_sse_enabled` OR `kms_master_key_id` present) |
| `aws_sns_topic` | `topic` | `encryption_at_rest` ← `kms_master_key_id` present |
| `aws_vpc` | `network` | — |
| `aws_subnet` | `subnet` | — |
| `aws_security_group` | `security_group` | `open_to_world`, `open_to_world_ports` — scan ingress blocks for `0.0.0.0/0` or `::/0`; port `"{from_port}"` or `"{from_port}-{to_port}"` |
| `aws_lb` / `aws_alb` | `load_balancer` | `internal`; `scheme` = `"internal"`/`"internet-facing"` |
| `aws_api_gateway_rest_api` | `api_gateway` | — |
| `aws_route53_zone` | `dns_zone` | — |
| `aws_cloudfront_distribution` | `cdn` | — |
| `aws_secretsmanager_secret` | `secret_store` | — |
| `aws_kms_key` | `kms_key` | `rotation_enabled` ← `enable_key_rotation` |
| `aws_iam_role` | `iam_role` | — |
| *anything else* | `unknown` | node emitted with no properties + warning `W004` |

All nodes also get `tags` (sorted `"key=value"` list from the `tags` map) and `region`
(`null` in v1 — region isn't reliably knowable from HCL; the cloud ingestor will fill it).

### 5.2 Modifier resources

Some AWS features are separate resources that *configure* another resource (the three
`aws_s3_bucket_*` rows above). These do **not** become nodes. Processing is two-pass:
pass 1 creates all nodes; pass 2 applies modifiers to the node their `bucket` attribute
references. Modifier referencing an unknown bucket → warning `W002`, modifier dropped.
A property never set by resource or modifier stays `null` (e.g. an S3 bucket with no
encryption configuration resource has `encryption_at_rest: null` — the *rules* decide how
severe unknowns are, not the parser).

## 6. Edges from references

HCL values like `subnet_id = aws_subnet.private.id` are parsed by `python-hcl2` into
strings containing `${aws_subnet.private.id}`. Scan every string value of every resource
with the regex `\$\{([a-z0-9_]+)\.([a-zA-Z0-9_-]+)(\.[a-zA-Z0-9_.\[\]"]+)?\}` (also handle
bare references where hcl2 emits them unwrapped):

- Referenced resource exists in the graph → emit an edge, deduplicated:
  - `aws_subnet` referenced via `subnet_id`-like attributes → reversed `contains` edge
    (subnet `contains` the referencing resource); same for `vpc_id` → network `contains` X.
  - LB target/listener references pointing at compute/container/function → `routes_to`.
  - Everything else → `depends_on` from the referencing node to the referenced node.
- Reference to `var.*`, `local.*`, `data.*`, `module.*` → not an edge (see §7).
- Reference to a resource not in the graph → warning `W002`, no edge.

## 7. Variables, locals, and modules

- **Variables:** collect `variable` blocks; a `${var.x}` whose variable has a literal
  `default` is substituted. No default → value `null` + `W006`.
- **Locals:** substitute literal-valued locals; locals containing expressions → `null` + `W006`.
- **`.tfvars`:** out of scope v1 (backlog).
- **Local modules** (`source = "./modules/networking"`): parse the module directory with
  `module_path` extended (§4); a module call's literal arguments are that module's variable
  values. Depth limit 5 (cycle guard) → deeper: `W003`. **Remote modules** (any non-`./`
  non-`../` source): `W003`, skipped.

## 8. Determinism

Files processed in sorted path order; resources in file order; nodes/edges sorted by id in
the final graph (spec 001 canonical form guarantees this); warnings sorted by
(file, line, code). Same directory content → byte-identical `to_json(graph)`.

## 9. Acceptance criteria

Build fixture Terraform projects under `tests/fixtures/terraform/` — each a small directory
with an expected-graph JSON file next to it. Minimum fixtures:

1. **`simple/`** — one VPC, one subnet, one `aws_instance` referencing the subnet, one
   encrypted `aws_db_instance`. Assert: 4 nodes with exact ids/types/properties;
   `contains` edges network→subnet is *not* implied (no reference) but subnet→instance is;
   instance `depends_on` nothing else; db properties exactly as written.
2. **`s3_modifiers/`** — bucket + separate encryption-config + public-access-block resources.
   Assert bucket node has `encryption_at_rest: true`, `public_access_blocked` correct, and
   modifiers produced no nodes.
3. **`variables/`** — property set via `var` with default, via `var` without default, via
   literal local. Assert substituted value / `null`+`W006` / substituted value.
4. **`local_module/`** — root calls `./modules/net`. Assert module resources appear with
   `tf:root.net:` ids and module variables got the call-site literals.
5. **`open_sg/`** — security group with `0.0.0.0/0` on 22 and a private ingress. Assert
   `open_to_world: true`, `open_to_world_ports == ["22"]`.
6. **`broken/`** — one syntactically invalid file among valid ones. Assert valid resources
   still parsed, exactly one `W001` naming the bad file, no exception.
7. **`unmapped/`** — an `aws_wafv2_web_acl`. Assert node type `unknown` + `W004`.
8. **Determinism test** — parse fixture 1 twice into fresh processes/orders; identical JSON.
