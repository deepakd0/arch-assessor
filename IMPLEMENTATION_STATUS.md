# Implementation Status — Phase 1

**Last updated: 2026-07-05.** ~~Struck-out~~ items are **built, tested, and passing** (104 tests,
`ruff` clean, `pip-audit` zero CVEs, cross-process determinism verified). Unstruck items are
open work — each one names the spec section that defines it, so any model or developer can
pick it up without this conversation's context.

**How to verify the done items yourself:**

```bash
python3.13 -m venv venv && ./venv/bin/pip install -e . pytest
./venv/bin/pytest tests/ -q          # 104 passed
./venv/bin/archscan scan tests/fixtures/terraform/simple
```

## Core pipeline (specs 001–006)

- ~~**Spec 001 — Architecture graph**: dataclasses, closed node/edge taxonomies, tri-state properties (`null` = undeterminable), validation with aggregated problems, canonical byte-deterministic JSON, round-trip (`src/archassessor/graph/model.py`)~~
- ~~**Spec 003 — Rule format & loader**: YAML rules via `yaml.safe_load` only, full condition grammar (all 11 leaf operators incl. `has_tag_key`, `all`/`any`/`none` combinators, `related` edges), framework-mapping validation, error aggregation across files, duplicate-id rejection (T10), regex length cap (T3) (`src/archassessor/rules/`)~~
- ~~**Spec 003 §7 — Built-in pack**: 20 rules (SEC×11, REL×4, NET×1, OPS×3, DATA×1) with descriptions, remediations, SOC 2 mappings (`src/archassessor/rules/builtin/`)~~
- ~~**Spec 004 — Evaluation engine**: pure function, exact Kleene three-valued truth tables, deterministic detail templates, subjects/`where` filtering, score formula (spec example 70 verified), framework rollup (satisfied/gap/unknown/not_assessed), `external_findings` SARIF extension point, purity + determinism tested (`src/archassessor/engine/`)~~
- ~~**Spec 002 — Terraform parser**: offline HCL via python-hcl2 8.1.2 (incl. 8.x quote/`__is_block__` normalization), 22-type resource mapping table, S3 modifier resources (two-pass), variables/locals substitution, local modules with dotted ids + call args, reference-derived edges (`contains`/`routes_to`/`depends_on`), warnings W001–W008, graceful degradation on broken files (`src/archassessor/ingest/terraform/`)~~
- ~~**Spec 005 — Report renderers**: Markdown (full section structure incl. "Why it matters" + unknowns section), self-contained HTML (inline CSS, `html.escape` everywhere, XSS-tested, severity never color-only), JSON with opt-in `generated_at`; fixed legal disclaimer in all formats (`src/archassessor/report/`)~~
- ~~**Spec 006 — CLI**: `archscan scan|graph|rules list`, exit codes 0/1/2/3, `--fail-on` matrix, `--format md|html|json`, `--rules/--no-builtin/--framework/--include-passes/--timestamp/--quiet`, stdout/stderr stream discipline, atomic `--output` writes, stderr summary line (`src/archassessor/cli/main.py`)~~
- ~~**Test suite**: 104 tests — truth tables, Kleene, related, score, rollup, purity, determinism, 7 Terraform fixtures, XSS/YAML-code-exec abuse cases, CLI e2e incl. exit-code matrix (`tests/`)~~
- ~~**Packaging**: `pyproject.toml` (hatchling, `archscan` entry point, pinned deps hcl2 8.1.2 / PyYAML 6.0.3), `pip install -e .` verified, `pip-audit` zero CVEs, `ruff check` + `ruff format` clean~~

## Open work (ordered roughly by value; each item is self-contained)

### Correctness & spec completion

1. **Golden-file tests** (spec 005 §7.1, spec 009): commit expected `.md`/`.html`/`.json` outputs for a fixture assessment and byte-compare. Current tests assert structure, not full bytes.
2. **`mypy --strict` compliance** (NFR-M2): code has type hints but was never run through strict mypy; CI's `lint-and-type` job will likely fail until annotations are tightened (hcl2 has no stubs — needs `ignore_missing_imports` for it).
3. **Rule pack to 25+ rules** (spec 003 §7): missing BASE-NET-002 (internet-facing LB surfacing), BASE-NET-003 (DB/LB subnet separation — needs design decision, see spec note), and ISO 27001/PCI-DSS mappings on more rules.
4. **Spec 002 leftovers**: `.tfvars` files; `aws_s3_bucket_logging` sets `logging_enabled` but has no test; `count`/`for_each` warning (W005) exists but expansion doesn't; remote-module W003 has no test; W007 (5 MB cap) and W008 (symlink escape) implemented but untested — write the hostile fixtures (spec 009 §4 T1/T4).
5. **Property-based tests** (spec 009 §3): `hypothesis` generators for graph round-trip, order insensitivity, engine totality. Not started.
6. **Benchmarks** (spec 009 §5, NFR-P1–P3): `tests/gen_fixture.py` synthetic repo generator + timing/memory tests. Not started. Note: `Graph.node_by_id` is O(n) — fine at fixture scale, needs an id→node index dict before the 5k-resource target.
7. **Coverage gate** (spec 009 §2): wire `--cov-fail-under=90` + 100%-branch check on `engine/conditions.py` into CI once mypy passes.

### Process & repo

8. **SME sign-off on SOC 2 mappings** (spec 011 §7): mappings currently author-proposed only. Either recruit a reviewer and record sign-offs in `packs/builtin/MAPPING-REVIEWS.md`, or strip mappings before any public 0.1.0 (spec 011 says an unmapped pack is acceptable; unsigned mappings are not).
9. **Rule PR template** (spec 011 §3): `.github/PULL_REQUEST_TEMPLATE/rule.md` with the mapping-justification checklist.
10. **Docs refresh**: GETTING_STARTED.md and CONTRIBUTING.md still say "nothing is implemented"; README roadmap row for Phase 1 needs updating to "core implemented". `SECURITY.md` contains a placeholder email — replace with a real contact.
11. **Corpus job** (spec 009 §6): `tests/corpus/repos.txt` + weekly CI workflow cloning pinned real-world Terraform repos.
12. **Release automation** (spec 010 §4): tag-triggered build + PyPI trusted publishing; check name availability before first publish.

### Phase 2 (specs not yet written — write specs first, then build)

13. Custom guardrails UX + rule-authoring guide with worked examples (spec 010 §7).
14. GitHub Action packaging of the CLI (spec 006 was designed for this; no breaking changes expected).
15. SARIF importer feeding `evaluate(external_findings=…)` — the engine-side hook is ~~done~~ and tested; the SARIF file parser is not.
16. `--strict-unknown` flag, `archscan.toml` config file, `--verbose` logging (NFR-O1).

## Known deviations from spec (deliberate, documented)

- **Spec 002 §3** says "parse all `*.tf` recursively"; implementation parses the root directory + directories reachable via local `module` calls — matching Terraform's own semantics and avoiding double-parsing module dirs. Revisit only if pilot users keep unreferenced subdirectories they expect scanned.
- **Spec 005 §3** renderer API: framework filtering (`--framework`) is done by the CLI shallow-copying `assessment.frameworks` before rendering, not by a renderer parameter.
- **requirements.txt** pins hcl2 **8.1.2** / PyYAML **6.0.3** (the versions that actually exist and install), not the speculative pins previously written into spec-phase docs.
