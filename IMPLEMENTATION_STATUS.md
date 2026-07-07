# Implementation Status — Phase 1

**Last updated: 2026-07-06.** ~~Struck-out~~ items are **built, tested, and passing**
(193 tests + 3 benchmark + 6 corpus; `ruff` clean; `mypy --strict` clean; `pip-audit`
zero CVEs; 97% branch coverage; cross-process determinism verified). Unstruck items
are open work — each names the spec section that defines it, so any model or developer
can pick it up without this conversation's context.

**How to verify the done items yourself:**

```bash
python3.13 -m venv venv && ./venv/bin/pip install -e . pytest pytest-cov hypothesis
./venv/bin/pytest tests/ -q          # 193 passed, 9 deselected (benchmark/corpus opt-in)
./venv/bin/archscan scan tests/fixtures/terraform/simple
```

## Session history

- **2026-07-05 (Fable review):** fixed 5 defects — (a) `from_json` TypeError on hostile
  non-integer `source.line`; (b) CLI atomic-write temp-file leak on write failure; (c) W008
  symlink-escape warning reported the absolute *target* path, not the in-repo name; (d) HCL
  attributes resolving to nested structures could leak spec-invalid property values into the
  graph (now clamped via `_coerce_props`); (e) relationship rules were O(N·E) — engine now
  builds an O(1) `_GraphIndex` per `evaluate()`. Added the abuse suite (`test_hostile.py`,
  threats T1/T3/T4 + hostile-JSON + safe_load guard) and property suite (`test_properties.py`).
- **2026-07-06 (Sonnet):** closed golden-file tests, benchmarks, corpus job, coverage
  (86%→97%), NET-002, spec-002 leftover tests, rule PR template, SECURITY.md contact.
- **2026-07-06 (Opus review):** independently re-verified all gates; audited every framework
  mapping for control-ID validity and semantic fit → recorded a **technical pre-review** in
  `src/archassessor/rules/builtin/MAPPING-REVIEWS.md` (flags 3 questionable mappings for the
  human SME); refreshed GETTING_STARTED.md (was still claiming "no code implemented").

## Core pipeline (specs 001–006) — all ~~done~~

- ~~**Spec 001 — Architecture graph**: dataclasses, closed node/edge taxonomies, tri-state properties (`null` = undeterminable), validation with aggregated problems, canonical byte-deterministic JSON, round-trip (`src/archassessor/graph/model.py`)~~
- ~~**Spec 003 — Rule format & loader**: YAML rules via `yaml.safe_load` only, full condition grammar (11 leaf operators incl. `has_tag_key`, `all`/`any`/`none` combinators, `related` edges), framework-mapping validation, error aggregation across files, duplicate-id rejection (T10), regex length cap (T3); loader/schema at 100% coverage (`src/archassessor/rules/`)~~
- ~~**Spec 003 §7 — Built-in pack**: **21 rules** (SEC×11, REL×4, NET×2, OPS×3, DATA×1) with descriptions, remediations, SOC 2 mappings (+ ISO 27001 / PCI-DSS on a few); loads cleanly (`src/archassessor/rules/builtin/`)~~
- ~~**Spec 004 — Evaluation engine**: pure function, exact Kleene three-valued truth tables (100%-branch on `conditions.py`), deterministic detail templates, subjects/`where` filtering, score formula (spec example 70 verified), framework rollup, `external_findings` SARIF hook, O(1) `_GraphIndex`, purity + determinism tested (`src/archassessor/engine/`)~~
- ~~**Spec 002 — Terraform parser**: offline HCL via python-hcl2 8.1.2 (incl. 8.x quote/`__is_block__` normalization), 22-type resource mapping table (100% coverage), S3 modifier resources (two-pass), variables/locals substitution, local modules with dotted ids + call args, reference-derived edges, warnings W001–W008, graceful degradation (`src/archassessor/ingest/terraform/`)~~
- ~~**Spec 005 — Report renderers**: Markdown, self-contained HTML (`html.escape` everywhere, XSS-tested, severity never color-only), JSON with opt-in `generated_at`; fixed legal disclaimer in all three; **golden-file tests** byte-compare all formats (`src/archassessor/report/`)~~
- ~~**Spec 006 — CLI**: `archscan scan|graph|rules list`, exit codes 0/1/2/3, `--fail-on` matrix, `--format md|html|json`, all flags, stdout/stderr discipline, atomic `--output` writes (`src/archassessor/cli/main.py`)~~
- ~~**Packaging & CI**: `pyproject.toml` (hatchling, `archscan` entry point, pinned deps), `pip install -e .` verified, `pip-audit` zero CVEs, `ruff` + `mypy --strict` blocking in CI, cross-OS matrix, determinism job, benchmark job, weekly corpus job~~

## Open work (ordered by value; each item is self-contained)

### Human gate (cannot be completed by a model)

1. **SME sign-off on framework mappings** (spec 011 §7). A **technical pre-review** now
   exists at `src/archassessor/rules/builtin/MAPPING-REVIEWS.md`: it verifies every control
   ID is real and assesses plausibility, and flags **three questionable mappings** for an SME
   — `CC6.7` on at-rest encryption (SEC-001/002; CC6.7 is transmission-oriented), `A1.3` on
   backup retention (REL-002; A1.3 is recovery *testing*), and `CC1.3` on resource tagging
   (OPS-001/002; CC1.3 is org structure). Before any public `0.1.0`, a qualified human must
   sign each mapping to keep or instruct which to strip (an unmapped pack is acceptable; an
   unsigned mapping is not). Until then the report's disclaimer already scopes output as
   "findings, not compliance."

### Correctness & spec completion

2. **Rule pack breadth** (spec 003 §7): pack is 21 rules. ~~NET-002 (internet-facing LB surfacing) added.~~ NET-003 (DB/LB shared-subnet) is **deferred by design** — the spec itself marks it "needs graph traversal beyond v1 conditions"; implementing it requires a condition-language extension (multi-hop reachability), which should be its own spec'd change, not an ad-hoc rule. More ISO 27001 / PCI-DSS mappings are gated on item 1 (SME).
3. **Release automation** (spec 010 §4): tag-triggered build + PyPI trusted publishing (OIDC); check the `arch-assessor` name is available on PyPI before first publish. Not started.

### Phase 2 (write specs first, then build)

4. Custom guardrails UX + rule-authoring guide with worked examples (spec 010 §7).
5. GitHub Action packaging of the CLI (spec 006 was designed for this; exit-code contract already stable).
6. SARIF importer feeding `evaluate(external_findings=…)` — the engine-side hook is ~~done~~ and tested; the SARIF *file parser* is not.
7. `--strict-unknown` flag, `archscan.toml` config file, `--verbose` logging (NFR-O1).

## Recently closed (2026-07-06, was open)

- ~~**Golden-file tests** (spec 005 §7.1): `tests/test_report_golden.py` + `tests/fixtures/reports/` byte-compare MD/HTML/JSON for a rich and an empty assessment; regen via `ARCHASSESSOR_WRITE_GOLDEN=1`.~~
- ~~**`mypy --strict`** (NFR-M2): clean on all 20 source files; CI step blocking.~~
- ~~**Property-based tests** (spec 009 §3): `tests/test_properties.py` (hypothesis).~~
- ~~**Benchmarks** (spec 009 §5, NFR-P1–P3): `tests/gen_fixture.py` + `tests/test_benchmarks.py`, opt-in `benchmark` marker, own Linux CI job. Measured well within budget (1k/5k resources, peak memory).~~
- ~~**Coverage gate** (spec 009 §2): 97% overall, 100%-branch on `conditions.py`, 100% on loader/schema/mappings; CI floor raised to 95.~~
- ~~**Corpus job** (spec 009 §6): `tests/corpus/repos.txt` (6 pinned real-world terraform-aws-modules repos, verified SHAs) + `tests/test_corpus.py` + weekly `.github/workflows/corpus.yml`. All 6 parse clean.~~
- ~~**Spec 002 leftover tests**: `aws_s3_bucket_logging` modifier, `count`/`for_each` W005, remote-module W003, dynamodb/queue/topic/LB encryption variants, duplicate-address/self-loop/orphan-reference edge cases — all covered.~~
- ~~**Rule PR template** (spec 011 §3): `.github/PULL_REQUEST_TEMPLATE/rule.md`.~~
- ~~**Docs refresh**: GETTING_STARTED.md rewritten to lead with the working CLI; SECURITY.md now uses GitHub private vulnerability reporting (enabled on the repo), not a placeholder email; README already updated.~~

## Known deviations from spec (deliberate, documented)

- **Spec 002 §3** says "parse all `*.tf` recursively"; implementation parses the root module + directories reached via local `module` calls — matching Terraform's own semantics and avoiding double-parsing module dirs.
- **Spec 002 §7** lists `.tfvars` as *out of scope for v1* (backlog) — so it is correctly **not** implemented; it is not a "leftover."
- **Spec 005 §3** renderer API: `--framework` filtering is done by the CLI shallow-copying `assessment.frameworks` before rendering, not via a renderer parameter.
- **requirements.txt** pins hcl2 **8.1.2** / PyYAML **6.0.3** (the versions that actually install), not the speculative pins in early spec-phase docs.
