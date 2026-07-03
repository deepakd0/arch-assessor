# Spec 009 — Test Strategy

**Depends on:** specs 000–008. Per-spec acceptance criteria define *feature* correctness;
this document defines the *system-level* quality gates and how they run in CI.

## 1. Test layers

| Layer | Lives in | What it proves | Gate |
|-------|----------|----------------|------|
| Unit | `tests/test_*.py` | Each spec's acceptance criteria (specs 001–006 list them) | all pass |
| Golden files | `tests/fixtures/**` + expected outputs | Byte-exact formats: graphs, reports | all pass |
| End-to-end | `tests/test_cli.py` | Full pipeline through `main(argv)` in-process | all pass |
| Property-based | `tests/test_properties.py` | Invariants under generated inputs (§3) | all pass |
| Abuse/fuzz | `tests/test_hostile.py` | Threat-model mitigations (§4) | all pass |
| Benchmarks | `tests/test_benchmarks.py` | NFR-P1..P5 budgets (§5) | pass, may be skipped locally |
| Corpus | `tests/corpus/` (§6) | Real-world Terraform doesn't crash us | scheduled CI only |

## 2. Coverage gates (enforced in CI via `pytest --cov`)

- `engine/` (spec 004): **100 % branch coverage of `conditions.py`** — the truth tables are
  the product's contract; an untested branch there is a latent lie to customers.
- `graph/`, `rules/`, `report/`: ≥ 90 % line coverage.
- `ingest/terraform/`: ≥ 85 % (HCL wrangling has long tails; fixtures grow it over time).
- `cli/`: ≥ 90 % via the e2e tests.

Coverage is a floor, not a goal — a PR that games coverage without asserting behavior fails
review.

## 3. Property-based tests (`hypothesis`, dev-only dependency)

1. **Graph round-trip:** for arbitrary valid graphs (generated within the spec-001 taxonomy),
   `from_json(to_json(g)) == g` and `to_json` is canonical-stable.
2. **Order insensitivity:** node/edge/rule insertion order never changes `assessment_to_json`.
3. **Engine totality:** for arbitrary valid graph × arbitrary valid rule, `evaluate` returns
   (never raises), every verdict ∈ {pass, fail, unknown}, and score ∈ [0, 100].
4. **Kleene laws:** `all([x]) == x`, `none([x]) == not-table of x`, `any` is commutative in
   verdict for generated child sets.
5. **Renderer totality:** any valid assessment renders in all three formats; HTML output
   never contains an unescaped `<` from a property value.

## 4. Abuse suite (threat model, spec 008)

One test per threat id, using `tests/fixtures/hostile/`:
T1 oversized/deep files → skipped with `W007`, run finishes within budget; T2 `!!python/object`
rule → load error, sentinel not executed; T3 evil regex + long property → completes < 2 s,
verdict `unknown`; T4 symlink escape + cycle → skipped with `W008`, no read outside root
(assert via opened-paths spy); T5 script-y names → escaped in HTML and inert in Markdown;
T10 builtin id collision → load error. Plus the two global guards: the `yaml.load(` source
grep and the no-socket monkeypatch around a full scan (NFR-C3).

## 5. Benchmarks

Fixture generator `tests/gen_fixture.py --resources N` emits synthetic-but-realistic repos
(mixed resource types, reference density ~2 edges/node). Benchmarks time `main(argv)`
end-to-end at N=1,000 and N=5,000 against NFR-P1/P2 and check peak `tracemalloc` against
NFR-P3. Marked `@pytest.mark.benchmark`; run in CI on Linux only (stable timings), 2×
budget tolerance to absorb runner noise.

## 6. Real-world corpus (scheduled CI, not per-PR)

A pinned list (`tests/corpus/repos.txt`) of ~10 popular open-source Terraform repos
(terraform-aws-modules/vpc, eks, rds, etc.) at pinned commits. Weekly CI job clones each and
asserts: parser never raises, warnings are only known codes, scan completes, exit code ∈
{0, 1}. Failures file issues — this is the primary discovery mechanism for Phase 2 parser
priorities. (Not run per-PR: network + size. The only network-touching job, and it never
touches product code paths' offline guarantee.)

## 7. CI pipeline (GitHub Actions, from first commit)

Per PR and on main:
1. `ruff check` + `ruff format --check` + `mypy --strict src/`
2. Full pytest (unit/golden/e2e/property/abuse) on **ubuntu + macos + windows**, Python 3.13
3. Coverage gates (§2)
4. Benchmarks (ubuntu)
5. `pip-audit -r requirements.txt --no-deps --disable-pip` — zero findings
6. **Determinism job:** run `archscan scan` twice on the largest fixture in separate
   processes with `PYTHONHASHSEED` different per run → `diff` must be empty. This is the
   product guarantee, tested the blunt way.

Weekly: corpus job (§6) + `pip-audit` re-run against fresh advisory data.

## 8. Definition of done (any Phase 1 feature)

Spec acceptance tests pass · relevant property/abuse tests extended · coverage gates hold ·
CI green on all three OSes · golden files updated deliberately (never regenerated blindly —
diff reviewed line by line) · no new runtime dependency without an ADR.
