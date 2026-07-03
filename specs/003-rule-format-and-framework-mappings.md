# Spec 003 — Rule Format & Framework Mappings

**Depends on:** specs 000, 001.
**Consumed by:** the evaluation engine (004) and CLI (006).

## 1. Purpose

Define how architecture rules are written (YAML), loaded, and validated — including the
compliance **framework mappings** that let one rule serve as evidence for controls in SOC 2,
ISO 27001, PCI-DSS, etc. Also defines the built-in starter rule pack (~30 rules) that gives
users a meaningful assessment in their first run.

Rules are **declarative data, not code**. Users never write Python to add a rule; this is
what makes rules safe to share, diff, review, and run on untrusted repos.

## 2. Scope

**In scope:** the YAML schema; the condition language (match + assert); the loader/validator
(`archassessor.rules`); the built-in pack (§7) with SOC 2 mappings.
**Non-goals:** evaluation semantics beyond what's needed to define the format (spec 004 owns
evaluation); custom Python plugin rules (Phase 2 backlog); ISO 27001/PCI-DSS pack *content*
(later phases — but the mapping *mechanism* ships now and the built-in pack may include
mappings for them where obvious).

## 3. Rule file format

One YAML file may contain one rule (a mapping) or several (a list). Full example:

```yaml
schema_version: "1.0"
id: BASE-SEC-001
title: Databases must be encrypted at rest
severity: high              # info | low | medium | high | critical
category: security          # security | reliability | cost | operations | data | network
description: >
  Unencrypted databases expose all stored data if storage media or snapshots
  are accessed. Encryption at rest is table stakes for handling customer data.
remediation: >
  Set `storage_encrypted = true` on the aws_db_instance / aws_rds_cluster.
  Existing instances require a snapshot-restore migration.
mappings:
  soc2: [CC6.1, CC6.7]
  iso27001: [A.8.24]
  pci_dss: ["3.5.1"]
match:
  node_type: database
assert:
  property: encryption_at_rest
  equals: true
```

### 3.1 Field reference

| Field | Required | Rules |
|-------|----------|-------|
| `schema_version` | yes (once per file) | `"1.0"` |
| `id` | yes | Unique across all loaded rules. Pattern `^[A-Z]{2,8}-[A-Z]{2,8}-\d{3}$` (e.g. `BASE-SEC-001`, `ACME-NET-042`). Prefix identifies the pack. |
| `title` | yes | ≤ 80 chars, imperative statement of the requirement. |
| `severity` | yes | `info`/`low`/`medium`/`high`/`critical`. |
| `category` | yes | closed set above. |
| `description` | yes | why the rule exists — shown in reports. |
| `remediation` | yes | how to fix — shown in reports. |
| `mappings` | no | map of framework key → list of control-id strings. v1 framework keys: `soc2`, `iso27001`, `pci_dss`, `hipaa`, `gdpr`. Unknown keys are a load error (typo protection). |
| `match` | yes | which nodes the rule applies to (§4). |
| `assert` | yes | the condition every matched node must satisfy (§5). |

## 4. `match` — selecting nodes

```yaml
match:
  node_type: database            # string or list of strings (OR)
  where:                         # optional extra filter, same condition language as assert
    property: engine
    equals: postgres
```

`node_type: any` matches all nodes. Nodes matching `match` are the rule's **subjects**; a
rule with zero subjects in a graph yields no verdicts (reported as "not applicable" — see 004).
The `where` filter uses the same condition grammar as `assert` (§5); nodes where the filter
is `unknown` are excluded from subjects.

## 5. `assert` — the condition language

A **condition** is one of:

**Leaf conditions** — always have `property` plus exactly one operator:

| Operator | Meaning |
|----------|---------|
| `equals: <value>` / `not_equals: <value>` | scalar comparison |
| `exists: true` / `exists: false` | property present and non-null / absent-or-null |
| `in: [a, b]` / `not_in: [a, b]` | membership |
| `gte: <number>` / `lte: <number>` | numeric comparison |
| `contains: <value>` / `not_contains: <value>` | list membership (property is a list) |
| `matches: <regex>` | full-match regex on string value |

**Combinators** — exactly one of, containing a list of conditions:

```yaml
assert:
  all:            # every sub-condition true      (also: any, none)
    - property: encryption_at_rest
      equals: true
    - any:
        - property: multi_az
          equals: true
        - property: backup_retention_days
          gte: 7
```

**Relationship conditions** — assert about the node's edges:

```yaml
assert:
  related:
    edge_type: depends_on      # contains | depends_on | routes_to
    direction: outgoing        # outgoing | incoming
    target_type: kms_key       # optional filter on the other node's type
    exists: true               # true = at least one such edge must exist; false = none may
```

### Three-valued logic (the part beginners get wrong)

Every condition evaluates to `pass`, `fail`, or `unknown` (spec 004 defines the exact
tables). A leaf condition on a property whose value is `null` — or absent, except for the
`exists` operator, which is specifically designed to test presence — is `unknown`, not
`fail`. The format just needs you to know: **`unknown` is a first-class outcome**, so rule
authors don't need "if the value is missing…" clauses.

## 6. Loader API (module `archassessor.rules`)

```python
@dataclass
class Rule:
    id: str; title: str; severity: str; category: str
    description: str; remediation: str
    mappings: dict[str, list[str]]
    match: Match
    condition: Condition           # parsed assert tree
    source_file: str

def load_rules(paths: list[Path]) -> list[Rule]:
    """Load every *.yaml/*.yml in the given files/directories (recursive).

    Raises RuleLoadError listing ALL problems across ALL files (file, rule id if
    known, message) — never just the first one. Result sorted by rule id.
    """

def load_builtin_pack() -> list[Rule]:
    """Load the pack shipped inside the package (archassessor/rules/builtin/)."""
```

Load-time validation: every field-reference rule in §3.1; operator names valid; combinators
non-empty; regexes compile; severity/category/framework keys in their closed sets; duplicate
ids across files rejected; `match.node_type` values exist in the spec-001 taxonomy.

## 7. Built-in starter pack (`BASE-*`)

Ship these ~30 rules as YAML files in `archassessor/rules/builtin/`, one category per file.
Each needs real `description`/`remediation` prose (write it for a mid-level engineer).
Severities and SOC 2 mappings as listed; add `iso27001`/`pci_dss` mappings where the author
is confident, otherwise omit.

**Security (`BASE-SEC-*`)**
| id | title | sev | match → assert (sketch) | soc2 |
|----|-------|-----|--------------------------|------|
| 001 | Databases must be encrypted at rest | high | database → `encryption_at_rest equals true` | CC6.1, CC6.7 |
| 002 | Object storage must be encrypted at rest | high | storage → `encryption_at_rest equals true` | CC6.1, CC6.7 |
| 003 | Queues must be encrypted at rest | medium | queue → `encryption_at_rest equals true` | CC6.1 |
| 004 | Topics must be encrypted at rest | medium | topic → same | CC6.1 |
| 005 | Databases must not be publicly accessible | critical | database → `publicly_accessible not_equals true` | CC6.1, CC6.6 |
| 006 | Storage buckets must block public access | critical | storage → `public_access_blocked equals true` | CC6.1, CC6.6 |
| 007 | No security group open to the world on all ports | critical | security_group → `none:[open_to_world_ports contains "0-65535"]` | CC6.6 |
| 008 | SSH must not be open to the world | high | security_group → `not_contains "22"` on `open_to_world_ports` | CC6.6 |
| 009 | RDP must not be open to the world | high | same, port 3389 | CC6.6 |
| 010 | KMS keys must have rotation enabled | medium | kms_key → `rotation_enabled equals true` | CC6.1 |
| 011 | Compute instances should not have public IPs | medium | compute → `public_ip not_equals true` | CC6.6 |

**Reliability (`BASE-REL-*`)**
| 001 | Production databases should be multi-AZ | high | database where `engine not_equals dynamodb` → `multi_az equals true` | A1.2 |
| 002 | Databases must retain backups ≥ 7 days | high | database → `backup_retention_days gte 7` | A1.2, A1.3 |
| 003 | Databases should enable deletion protection | medium | database → `deletion_protection equals true` | A1.2 |
| 004 | Storage buckets should enable versioning | low | storage → `versioning_enabled equals true` | A1.2 |

**Network (`BASE-NET-*`)**
| 001 | Every compute instance must live in a subnet | medium | compute → `related incoming contains from subnet exists true` | CC6.6 |
| 002 | Load balancers fronting the internet must be intentional | info | load_balancer where `scheme equals internet-facing` → `exists true` on `scheme` (surfacing rule: always "fails" into an info finding listing internet-facing LBs) | CC6.6 |
| 003 | Databases should not sit in the same subnet as internet-facing load balancers | medium | *(needs graph traversal beyond v1 conditions — mark `severity: info`, implement as far as `related` allows, note limitation in description)* | CC6.6 |

**Operations (`BASE-OPS-*`)**
| 001 | Every resource must carry an `owner` tag | medium | any → `tags contains-prefix owner=` → v1: `matches` on joined tags is not possible; implement as `contains` exact-match limitation documented, or add operator `has_tag_key` (see below) | CC1.3 |
| 002 | Every resource must carry an `environment` tag | low | any → `has_tag_key: environment` | CC1.3 |
| 003 | Storage buckets should have access logging | medium | storage → `logging_enabled equals true` | CC7.2 |

> **Extra operator required by OPS rules:** `has_tag_key: <string>` — leaf operator, passes
> when the node's `tags` list contains any entry starting `<string>=`. Add it to §5's table
> and the engine.

**Data (`BASE-DATA-*`)**
| 001 | Databases holding regulated data must reference a KMS key | medium | database where `has_tag_key: data-classification` → `related outgoing depends_on target kms_key exists true` | CC6.1 |

Pack acceptance: `load_builtin_pack()` loads with zero errors; every rule has non-empty
description and remediation; every `soc2` control id referenced matches pattern
`^(CC\d\.\d|A\d\.\d|C\d\.\d|P\d\.\d|PI\d\.\d)$`.

## 8. Acceptance criteria

1. The §3 example loads into a `Rule` with every field correct, mappings intact.
2. A file with 3 rules (list form) loads 3 rules, sorted by id.
3. Load-error aggregation: a directory with two bad files (one bad severity, one duplicate
   id) raises one `RuleLoadError` naming both files and both problems.
4. Unknown framework key `sco2` (typo) is a load error naming valid keys.
5. Invalid regex in `matches` is a load error with the regex error text.
6. Nested combinator (`all` containing `any` containing leaves) parses into the right tree.
7. `related` condition parses with defaults (`direction: outgoing`, no `target_type`).
8. Built-in pack: the pack acceptance checks in §7 pass; count ≥ 25 rules.
