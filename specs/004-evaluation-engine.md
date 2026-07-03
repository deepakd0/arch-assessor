# Spec 004 — Evaluation Engine

**Depends on:** specs 000, 001, 003.
**Consumed by:** report renderer (005) and CLI (006).

## 1. Purpose

The deterministic heart of the product: a **pure function** that takes a graph and a list of
rules and produces an assessment — verdicts, findings, score, and per-framework compliance
rollups. No I/O, no clock, no randomness, no network. Same inputs → identical output, always.
This purity is a product guarantee (customers gate CI on it), not a style preference.

## 2. Scope

**In scope:** condition evaluation (three-valued logic), verdict production, finding
construction, scoring, framework rollup, the `Assessment` data model and its canonical JSON.
**Non-goals:** loading anything from disk (003/002 own that); rendering (005); waivers/
acknowledged-findings (Phase 3); SARIF-imported findings (Phase 2 — but see §8 for the
extension point).

## 3. Public API (module `archassessor.engine`)

```python
def evaluate(graph: Graph, rules: list[Rule]) -> Assessment: ...
```

### Data model

```python
Verdict = Literal["pass", "fail", "unknown"]

@dataclass
class RuleResult:
    rule_id: str
    node_id: str
    verdict: Verdict
    detail: str          # §5.4 — human-readable, deterministic

@dataclass
class Finding:            # one per fail/unknown RuleResult
    rule_id: str; rule_title: str; severity: str; category: str
    node_id: str; node_name: str; node_type: str
    verdict: Verdict      # "fail" or "unknown"
    detail: str
    remediation: str
    mappings: dict[str, list[str]]
    source: SourceRef     # copied from the node — lets reports link to file:line

@dataclass
class FrameworkControlStatus:
    framework: str        # e.g. "soc2"
    control: str          # e.g. "CC6.1"
    status: Literal["satisfied", "gap", "unknown", "not_assessed"]
    rule_ids: list[str]   # rules mapped to this control that were evaluated

@dataclass
class Assessment:
    schema_version: str = "1.0"
    graph_metadata: dict[str, str]
    results: list[RuleResult]          # every rule × subject, sorted (rule_id, node_id)
    findings: list[Finding]            # sorted per §6
    not_applicable_rule_ids: list[str] # rules with zero subjects, sorted
    summary: Summary                   # counts + score, §5.5
    frameworks: list[FrameworkControlStatus]  # sorted (framework, control)

def assessment_to_json(a: Assessment) -> str:   # canonical: sorted keys, 2-space indent
```

## 4. Evaluation algorithm

For each rule (in id order):
1. **Subjects** = nodes matching `match.node_type` (or all, for `any`), then filtered by
   `match.where` if present — nodes whose `where` evaluates `pass` stay; `fail` and
   `unknown` are excluded.
2. Zero subjects → rule id goes to `not_applicable_rule_ids`; no results.
3. For each subject (in node-id order): evaluate the `assert` condition → one `RuleResult`.
4. `fail`/`unknown` results become `Finding`s (copying rule + node fields).

## 5. Condition semantics — the three-valued truth tables

This section is the contract; implement it exactly.

### 5.1 Leaf operators

Let `v` = the node's property value; "missing" = property absent OR `null`.

| Operator | missing → | otherwise |
|----------|-----------|-----------|
| `equals` / `not_equals` | `unknown` | `pass` iff `v ==` / `v !=` the operand (type-sensitive: `1 != "1"`, `True != "true"`) |
| `exists: true` | `fail` | `pass` |
| `exists: false` | `pass` | `fail` |
| `in` / `not_in` | `unknown` | membership check |
| `gte` / `lte` | `unknown` | `v` non-numeric → `fail` with type detail; else compare |
| `contains` / `not_contains` | `unknown` | `v` not a list → `fail`; else membership |
| `matches` | `unknown` | `v` not a string → `fail`; else `re.fullmatch` |
| `has_tag_key` | (tags missing/empty) `fail` | `pass` iff any tag starts `"<key>="` |

### 5.2 Combinators (Kleene logic)

| Combinator | pass when | fail when | else |
|------------|-----------|-----------|------|
| `all` | every child `pass` | any child `fail` | `unknown` |
| `any` | any child `pass` | every child `fail` | `unknown` |
| `none` | every child `fail` | any child `pass` | `unknown` |

Evaluate **all** children (no short-circuit) — needed for stable `detail` strings.

### 5.3 `related`

Collect the node's edges of `edge_type` in `direction`; if `target_type` given, keep only
edges whose other endpoint has that node type. `exists: true` → `pass` iff ≥ 1 remains,
else `fail`. `exists: false` → inverted. `related` never yields `unknown` in v1 (edges are
either present or not).

### 5.4 `detail` strings (deterministic explanations)

Every verdict carries a human explanation built from fixed templates — never free-form:
- pass leaf: `` `encryption_at_rest` is `true` (expected `true`) ``
- fail leaf: `` `multi_az` is `false` (expected `true`) ``
- unknown leaf: `` `publicly_accessible` could not be determined from the source ``
- combinator: join the *deciding* children's details with `"; "` (for `all`-fail: the
  failing children; for `any`-fail: all children; etc.)
- related fail: `` no outgoing `depends_on` edge to a `kms_key` node ``

### 5.5 Summary & score

```python
@dataclass
class Summary:
    nodes_total: int; rules_evaluated: int; rules_not_applicable: int
    results_pass: int; results_fail: int; results_unknown: int
    findings_by_severity: dict[str, int]   # all five severities, zero-filled
    score: int                             # 0–100
```

Score: start at 100; per **fail** finding subtract `critical: 15, high: 10, medium: 5,
low: 2, info: 0`; per **unknown** finding subtract half (7.5, 5, 2.5, 1, 0); sum, round
half-up, clamp to [0, 100]. Simple and explainable beats clever — the formula is printed in
the report (005).

## 6. Ordering (determinism)

- `results`: (rule_id, node_id). `findings`: (severity rank critical→info, rule_id, node_id).
- `frameworks`: (framework, control). All lists inside objects sorted. Two runs on equal
  inputs must produce byte-identical `assessment_to_json` output.

## 7. Framework rollup

For every framework key and control id appearing in any *evaluated* rule's `mappings`:

- Collect all evaluated rules mapping to that control. Control status:
  - any rule has ≥ 1 `fail` result → `gap`
  - else any rule has ≥ 1 `unknown` result → `unknown`
  - else at least one rule produced ≥ 1 `pass` result → `satisfied`
  - else (all mapped rules were not-applicable) → `not_assessed`

The rollup answers "which SOC 2 technical controls have passing evidence, which have gaps,
and which does this graph not exercise" — the compliance-readiness half of the product.
Wording in code and output: `satisfied` means *this tool's checks found no gaps*, never
"compliant" (spec 000 §6).

## 8. Extension point (build now, use in Phase 2)

`evaluate` accepts an optional `external_findings: list[Finding] = ()`. v1 behavior: they are
appended into `findings` (subject to the same sorting) and counted in summary/score/rollup
exactly like native ones. This is where the Phase 2 SARIF importer will plug in — keeping the
"single pane of glass" from requiring engine changes later. Test it with a hand-built finding.

## 9. Acceptance criteria

Hand-built graphs (no Terraform parser needed — this spec is testable standalone):

1. **Truth tables:** for each §5.1 operator, three tests: value satisfying, value violating,
   value missing/null. Assert exact verdict and exact `detail` string.
2. **Kleene:** `all`/`any`/`none` each tested with (pass,pass), (pass,fail), (pass,unknown),
   (fail,unknown) children.
3. **`related`:** edge present, absent, wrong type, wrong target_type, `exists: false` cases.
4. **Subjects:** `match.where` excludes `fail` and `unknown` nodes; rule with zero subjects
   lands in `not_applicable_rule_ids` and affects rollup as `not_assessed`.
5. **Score:** graph engineered to produce 1 critical fail + 1 high unknown + 2 medium fails
   → score = 100 − 15 − 5 − 10 = 70.
6. **Rollup:** one control mapped by two rules where rule A passes everywhere and rule B
   fails once → `gap`; A passes and B unknown → `unknown`; both pass → `satisfied`.
7. **Determinism:** shuffle input node/edge/rule construction order → byte-identical
   `assessment_to_json`.
8. **Purity guard:** `evaluate` called twice on the same objects returns equal results and
   does not mutate the input graph or rules (compare before/after serialization).
9. **External findings:** injected finding appears in findings, summary counts, and score.
