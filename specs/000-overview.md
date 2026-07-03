# Spec 000 — Overview, Conventions, and Glossary

Read this before implementing any other spec. It defines the vocabulary, the repository
layout, and the rules every implementer must follow. The other specs assume you know
everything on this page.

## 1. What we are building (Phase 1)

A command-line tool, `archscan`, that:

1. Reads a directory of Terraform files.
2. Converts them into an **architecture graph** (a JSON document of nodes and edges).
3. Evaluates a set of **rules** (YAML files) against that graph.
4. Produces a **report** (Markdown, HTML, or JSON) with findings, a score, and a
   per-framework compliance readiness rollup (SOC 2 in Phase 1).

The data flows in one direction:

```
Terraform files ──▶ [002 parser] ──▶ Graph ──▶ [004 engine] ──▶ Findings ──▶ [005 renderer] ──▶ Report
                                       ▲
                     Rules (YAML) ─────┘  (loaded per [003])
                     [006 CLI] orchestrates all of the above
```

Each numbered spec is one box. The interfaces between boxes are JSON-serializable Python
objects defined in spec 001 (graph), 003 (rules), and 004 (findings). If you implement your
box to its spec's acceptance tests, it will compose with the others.

## 2. Glossary

| Term | Meaning |
|------|---------|
| **Architecture graph** | The canonical model: nodes (things that exist — a database, a network, a load balancer) and edges (relationships between them). Defined in spec 001. |
| **Node** | One architectural element. Has a stable `id`, a `type` from a fixed taxonomy, a `name`, `properties`, and a `source` telling where it came from. |
| **Edge** | A directed relationship between two nodes (`contains`, `depends_on`, `routes_to`). |
| **Ingestor** | Any component that produces a graph from some source. Phase 1 has one: the Terraform parser (spec 002). |
| **Rule** | A machine-checkable statement about the graph, written in YAML ("every `database` node must have `encryption_at_rest: true`"). Defined in spec 003. |
| **Rule pack** | A directory of rules shipped together (e.g. the built-in baseline pack). |
| **Framework mapping** | Metadata on a rule linking it to compliance controls (e.g. SOC 2 CC6.1). One rule can map to controls in several frameworks. |
| **Verdict** | The outcome of one rule against one node: `pass`, `fail`, or `unknown` (the graph lacks the data to decide). |
| **Finding** | A recorded `fail` or `unknown` verdict, with severity, message, remediation, and source location. |
| **Assessment** | The complete result of one run: all verdicts, findings, score, framework rollup. |
| **Determinism** | Same inputs produce byte-identical outputs. See §4 — this is a hard requirement, not an aspiration. |

## 3. Repository layout

```
arch-assessor/
├── README.md
├── requirements.txt            # pinned, e.g. python-hcl2==7.3.1
├── pyproject.toml              # package metadata; console_scripts entry for `archscan`
├── specs/                      # these documents
├── src/
│   └── archassessor/
│       ├── __init__.py         # __version__ lives here
│       ├── graph/              # spec 001: model.py, validate.py
│       ├── ingest/
│       │   └── terraform/      # spec 002: parser.py, mappings.py
│       ├── rules/              # spec 003: loader.py, schema.py
│       │   └── builtin/        # spec 003 appendix: the starter pack (*.yaml)
│       ├── engine/             # spec 004: evaluate.py, conditions.py, scoring.py
│       ├── report/             # spec 005: markdown.py, html.py, json_out.py
│       └── cli/                # spec 006: main.py
└── tests/
    ├── fixtures/               # sample .tf projects, sample graphs, sample rules
    ├── test_graph.py
    ├── test_terraform_parser.py
    ├── test_rules_loader.py
    ├── test_engine.py
    ├── test_report.py
    └── test_cli.py
```

## 4. Non-negotiable engineering rules

1. **Determinism.** Anywhere a list is emitted (nodes, edges, findings, report sections),
   sort it by a documented key. Never iterate a `set` or rely on dict insertion order for
   output. No timestamps in canonical output (the JSON report has an optional
   `generated_at` that is *excluded* by default and only included with an explicit CLI flag).
   No randomness, no network calls, no LLM calls.
2. **Pure core.** The evaluation engine (spec 004) is a pure function. It does no I/O, reads
   no environment, and touches no globals. All I/O lives in the ingestors, loaders, and CLI.
3. **Fail loudly on our bugs, gracefully on user input.** Malformed user input (bad `.tf`,
   bad rule YAML) produces a clear error message naming the file and line, and a nonzero
   exit — never a stack trace. Internal invariant violations may raise.
4. **Python 3.13+, full type hints on all public functions, dataclasses for models.**
5. **Every public function has a docstring**; inline comments only where the code cannot
   speak for itself.
6. **Tests are part of the feature.** A spec is "done" when its acceptance criteria all have
   passing tests. Run `pytest tests/ -v` from the repo root.
7. **Dependencies:** minimal, pinned exactly in `requirements.txt`, audited with
   `pip-audit -r requirements.txt --no-deps --disable-pip` after any change. Zero CVE tolerance.
8. **UTF-8 everywhere; every file ends with a trailing newline.**

## 5. Versioning of data formats

The graph JSON and the rule YAML each carry a `schema_version` string, starting at `"1.0"`.
Any breaking change bumps the major number, and readers must reject major versions they do
not understand with a clear message. This lets Phase 2+ evolve formats without silently
misreading old files.

## 6. Wording discipline (legal)

Nothing in code, output, docs, or tests may claim the tool "certifies", "guarantees", or
"ensures" compliance. Approved vocabulary: *readiness*, *evidence*, *assessment*, *gap*.
The report renderer (spec 005) includes a fixed disclaimer for this reason — do not remove it.

## 7. Suggested implementation order for a beginner

1. Spec 001 first — it's pure data structures and the easiest win.
2. Spec 003's *loader* second (parse rule YAML into objects) — also pure data.
3. Spec 004 — the engine; test it against hand-written graphs and rules, no Terraform needed.
4. Spec 002 — the Terraform parser; the fiddliest part, but by now the target format is solid.
5. Spec 005, then 006 — rendering and wiring, both straightforward once the rest works.
