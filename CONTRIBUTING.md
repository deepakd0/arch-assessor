# Contributing to ArchAssessor

Thanks for considering building ArchAssessor! This guide explains how to work with the specs and implement features.

## Before you start

1. **Read [GETTING_STARTED.md](GETTING_STARTED.md)** — understand the project structure and how to navigate the specs.
2. **Read the relevant spec** — each spec has numbered acceptance criteria that define "done."
3. **Understand the design philosophy** — read [spec 000 §4](specs/000-overview.md) (non-negotiable engineering rules) and the [decisions/](decisions/README.md) (why we chose this, not that).

## Implementation workflow

### Phase 1 (the MVP spec'd in this repo)

**Build order (per spec 000 §7):**

1. **Graph schema (spec 001)** — the canonical data model.
   - Implement: Python dataclasses in `src/archassessor/graph/model.py`.
   - Test: spec 001 acceptance criteria → `tests/test_graph.py`.
   - Stop when: round-trip `to_json(from_json(g)) == g` passes, determinism test passes.

2. **Rule loader (spec 003)** — YAML parsing and validation.
   - Implement: `src/archassessor/rules/loader.py`, `schema.py`.
   - Test: spec 003 acceptance criteria → `tests/test_rules_loader.py`.
   - Stop when: load errors are correctly aggregated, builtin pack loads with zero errors.

3. **Evaluation engine (spec 004)** — the core logic.
   - Implement: `src/archassessor/engine/evaluate.py`, `conditions.py`, `scoring.py`.
   - Test: spec 004 acceptance criteria → `tests/test_engine.py`.
   - **Requirement: 100% branch coverage on `conditions.py`** (spec 009 §2).
   - Stop when: all three-valued truth tables pass, score formula is correct, framework rollup matches expected statuses.

4. **Terraform parser (spec 002)** — the tricky one, but by now the target format is solid.
   - Implement: `src/archassessor/ingest/terraform/parser.py`, `mappings.py`.
   - Test: spec 002 acceptance criteria + fixture-based tests → `tests/test_terraform_parser.py`.
   - Stop when: all six fixtures parse exactly as expected (graph equality), partial parsing degrades gracefully.

5. **Report renderer (spec 005)** — Markdown/HTML/JSON.
   - Implement: `src/archassessor/report/markdown.py`, `html.py`, `json_out.py`.
   - Test: spec 005 acceptance criteria + golden files → `tests/test_report.py`.
   - Stop when: golden files match byte-for-byte, XSS test passes, determinism holds.

6. **CLI (spec 006)** — glue it all together.
   - Implement: `src/archassessor/cli/main.py`.
   - Test: end-to-end tests → `tests/test_cli.py`.
   - Stop when: all subcommands work, exit codes are correct, help text is present.

### Cross-cutting requirements (apply to all steps)

- **Type hints:** every public function must have full type hints.
- **Docstrings:** one-liner per public function; inline comments only for non-obvious logic.
- **Tests:** spec acceptance criteria become pytest tests; each criterion is one or more test functions.
- **Coverage:** 90%+ line coverage on all modules except ingest/terraform (85%).
- **Determinism:** no timestamps, no set iteration, no locale-dependent formatting — test it explicitly (spec 009 §7.6).
- **No LLM in core:** the evaluation engine is a pure function; LLMs only at ingestion edges (Phase 3+).
- **Security:** threat T1–T10 (spec 008) each has a test in the abuse suite (spec 009 §4).
- **Dependency budget:** ≤ 3 runtime deps, pinned exactly, audited with `pip-audit`, zero CVEs (spec 007 NFR-M3).

## Working with specs

### When implementing a spec

1. **Copy the acceptance criteria from the spec** into your test file as a comment, one per test function.
2. **Implement to the spec, not your imagination.** If a spec says "sorted by rule_id", that's a test. If it says "deterministic", that's non-negotiable.
3. **Edge cases matter.** Read the "Edge cases" section of every spec carefully.
4. **Data structures are contracts.** If spec 001 says `Node.id: str`, don't make it `Node.id: Optional[str]` just to be flexible.

### When you find a spec ambiguity

1. **Check the ADRs** — maybe the decision is already there.
2. **Check TRACEABILITY.md** — maybe another spec clarified it.
3. **Open an issue** linking to the specific spec section. Title: "Spec 004 §5.2: what if both children of `any` are unknown?"

### When you need to change a spec

**Before Phase 1 is shipped:**

1. Open an issue with your reasoning.
2. Update the spec document.
3. Update all affected tests.
4. Update TRACEABILITY.md if requirements changed.

**After Phase 1 ships:**

1. Check [spec 010 §2](specs/010-lifecycle-versioning-support.md) — stable contracts can never break.
2. If it's not a stable contract, it's a minor-version bump, go ahead.
3. If it is a stable contract, file a major-version bump issue first.

## Repository structure for implementation

Once you start building, this is the shape of the repo:

```
arch-assessor/
├── (docs and specs as before)
│
├── src/archassessor/
│   ├── __init__.py                 __version__ goes here
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── model.py                Node, Edge, Graph dataclasses
│   │   └── validate.py             GraphValidationError, validate()
│   ├── ingest/
│   │   └── terraform/
│   │       ├── __init__.py
│   │       ├── parser.py           parse_directory(Path) → ParseResult
│   │       └── mappings.py         resource_type → (node_type, extractors)
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── loader.py               load_rules(), load_builtin_pack()
│   │   ├── schema.py               Rule, Match, Condition dataclasses
│   │   └── builtin/                (*.yaml files, the starter pack)
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── evaluate.py             evaluate(graph, rules) → Assessment
│   │   ├── conditions.py           condition evaluation (Kleene logic)
│   │   └── scoring.py              score calculation
│   ├── report/
│   │   ├── __init__.py
│   │   ├── markdown.py             render_markdown()
│   │   ├── html.py                 render_html()
│   │   └── json_out.py             render_json()
│   └── cli/
│       ├── __init__.py
│       └── main.py                 main(argv)
│
├── tests/
│   ├── fixtures/                   sample inputs and expected outputs
│   │   ├── terraform/              (fixture repos per spec 002 §9)
│   │   ├── hostile/                (abuse/fuzz inputs per spec 009 §4)
│   │   ├── rules/                  (sample rule files)
│   │   └── reports/                (golden files for spec 005)
│   ├── test_graph.py               spec 001 acceptance tests
│   ├── test_terraform_parser.py    spec 002 acceptance tests
│   ├── test_rules_loader.py        spec 003 acceptance tests
│   ├── test_engine.py              spec 004 acceptance tests
│   ├── test_report.py              spec 005 acceptance tests
│   ├── test_cli.py                 spec 006 + e2e tests
│   ├── test_properties.py          property-based tests (spec 009 §3)
│   ├── test_hostile.py             threat-model abuse suite (spec 009 §4)
│   └── test_benchmarks.py          NFR perf budgets (spec 009 §5)
│
├── requirements.txt                pinned dependencies (exactly 2–3 libs)
├── pyproject.toml                  package metadata, console_scripts entry
├── .github/workflows/
│   └── ci.yml                      pytest, coverage gates, pip-audit, determinism job
│
└── (other files as before)
```

## Code standards

### Python version

3.13+ only. No polyfills, no `from __future__ import annotations`.

### Imports

- Standard library first, then third-party, then local.
- No circular imports.
- Use full paths: `from archassessor.graph import Node`, not `from ..graph import Node`.

### Naming

- `snake_case` for functions, variables, modules.
- `PascalCase` for classes and exceptions.
- Public API is anything not starting with `_`.
- Exception classes end with `Error` (e.g. `GraphValidationError`).

### Type hints

Every public function:

```python
def parse_directory(root: Path) -> ParseResult:
    """Parse all .tf files under root. Return graph + warnings."""
    ...
```

### Testing

- Test names: `test_<feature>_<condition>_<expected>`. Example: `test_score_one_critical_fail_yields_85`.
- Fixture names: descriptive, under `tests/fixtures/`. Use the fixture name in test docstrings.
- Golden files: exact match, committed to git, reviewed on every change.
- Parametrized tests: `@pytest.mark.parametrize` when you have 3+ similar cases.

### Docstrings

**Public functions only** — one line, imperative, no redundancy:

```python
def evaluate(graph: Graph, rules: list[Rule]) -> Assessment:
    """Evaluate all rules against the graph; return findings and score."""
    ...
```

**Not** `"""Evaluates all rules against the graph and returns findings and a score."""` (redundant with the signature).

**Not** multi-line docstrings; if you need more, the code isn't clear enough.

## CI/CD gates

When you push, CI runs:

1. `ruff check` + `ruff format --check` (lint + format).
2. `mypy --strict src/` (type checking).
3. `pytest tests/ -v` (all tests, all platforms: ubuntu/macos/windows, Python 3.13).
4. Coverage gates: ≥ 90% overall, 100% on `engine/conditions.py`.
5. `pip-audit -r requirements.txt --no-deps --disable-pip` (zero CVEs).
6. **Determinism job:** run `archscan scan` on a fixture twice with different `PYTHONHASHSEED`, diff must be empty.

If any gate fails, the PR can't merge. This is intentional — it's the quality guarantee.

## Commit messages

- **First line:** imperative, under 70 characters. "Add graph schema", "Fix ReDoS in regex matching".
- **Body:** why, not what. The diff shows what changed; commit message explains why.
- Example:

```
Add Kleene three-valued verdict logic to evaluation engine

Replaces binary (pass/fail) with pass/fail/unknown so missing data
never produces a false pass. Spec 004 §5 defines exact truth tables.
Fixes spec 001 §2 acceptance criterion "handling null properties".
```

## Before you open a PR

- [ ] Read the relevant spec **thoroughly**.
- [ ] All acceptance criteria have passing tests.
- [ ] `pytest tests/ -v` passes on your machine (all tests).
- [ ] Type hints on all public functions.
- [ ] No hardcoded paths (everything relative).
- [ ] Determinism tests pass (if you changed output formatting).
- [ ] Golden files are reviewed (not regenerated blindly).
- [ ] Commit messages are clear.
- [ ] Your branch is up-to-date with `main`.

## License

By contributing, you agree that your work will be released under the Apache-2.0 license (see [ADR-0007](decisions/0007-license-and-open-core.md) — once accepted).

---

Questions? Open an issue. Want to discuss design before coding? Open a discussion. Good luck!
