# Spec 005 — Report Renderer

**Depends on:** specs 000, 004.
**Consumed by:** CLI (006).

## 1. Purpose

Turn an `Assessment` (spec 004) into something a human acts on: a Markdown report (default —
readable in a terminal, a PR comment, or a wiki), a standalone HTML report (shareable with
management), and machine-readable JSON (CI pipelines, future web platform). Reports are the
product's face; a mediocre engine with a great report beats the reverse.

## 2. Scope

**In scope:** Markdown, HTML, and JSON renderers with identical information content;
deterministic output; the compliance-readiness section; the fixed disclaimer.
**Non-goals:** diagrams (Phase 4); PDF (backlog); historical comparison between runs
(Phase 3); templating engines — v1 builds strings directly (no Jinja2 dependency; HTML uses
one Python f-string template with `html.escape` on every interpolated value).

## 3. Public API (module `archassessor.report`)

```python
def render_markdown(a: Assessment, *, include_passes: bool = False) -> str: ...
def render_html(a: Assessment, *, include_passes: bool = False) -> str: ...
def render_json(a: Assessment, *, generated_at: str | None = None) -> str: ...
```

`render_json` is `assessment_to_json` plus an optional `generated_at` field (ISO 8601,
injected by the CLI only when the user passes `--timestamp`; absent by default to preserve
byte-determinism — spec 000 §4).

## 4. Markdown report structure (exact section order)

```markdown
# Architecture Assessment Report

> This report is an automated readiness assessment. It provides evidence and gap
> analysis against the configured rules and framework mappings. It does not
> certify or guarantee compliance with any framework or regulation.

## Summary
- **Score: 70 / 100**  (100 minus severity-weighted penalties: critical 15, high 10,
  medium 5, low 2; unknowns count half)
- Nodes assessed: 24 | Rules evaluated: 28 | Not applicable: 3
- Findings: 1 critical, 2 high, 3 medium, 0 low, 1 info | Unknowns: 2

## Findings
### Critical
#### [BASE-SEC-006] Storage buckets must block public access — `assets` (storage)
- **Where:** `infra/s3.tf:14`
- **What:** `public_access_blocked` is `false` (expected `true`)
- **Why it matters:** <rule description>
- **Remediation:** <rule remediation>
- **Framework impact:** SOC 2 CC6.1, CC6.6
### High
...
### Needs data (unknown)
#### [BASE-SEC-001] ... — `analytics` (database)
- **What:** `encryption_at_rest` could not be determined from the source
- **How to resolve:** provide the missing configuration in source, or (Phase 4) declare it via the manual model
...

## Compliance readiness
### SOC 2
| Control | Status | Checked by |
|---------|--------|------------|
| CC6.1 | ⚠ gap | BASE-SEC-001, BASE-SEC-002, ... |
| CC6.6 | ✓ satisfied* | BASE-SEC-005, BASE-SEC-008 |
| CC7.2 | ? unknown | BASE-OPS-003 |
| A1.2 | – not assessed | BASE-REL-001 |
*satisfied = this tool's checks found no gaps in the controls it covers.

## Rules not applicable to this architecture
BASE-DATA-001, ...

## About this assessment
Tool version, rule pack ids + rule counts, graph source (metadata), formula footnote.
```

Rendering rules:
- Severity sections appear only if non-empty; "Needs data (unknown)" is always its own
  section after the severity sections — unknowns are a call to action, not noise.
- Every finding shows `file:line` when the node's `SourceRef` has them.
- One framework subsection per framework present in `a.frameworks`, alphabetical.
- `include_passes: true` appends a `## Passed checks` section (rule id, node id, one line
  each) — off by default to keep reports short.
- The disclaimer blockquote is mandatory and byte-fixed (spec 000 §6). Its wording lives in
  one constant shared by all three renderers' metadata.

## 5. HTML report

Same content and order as Markdown, self-contained single file: inline `<style>` (no external
assets, no JS, no CDN — it must open on an airgapped machine and attach to an email).
Sensible defaults: max-width ~900px, severity color coding (critical `#b91c1c`, high
`#ea580c`, medium `#d97706`, low `#65a30d`, info/unknown `#64748b`), findings as cards,
controls as a table. Every interpolated value passes through `html.escape` — node names come
from user repos and are hostile input (a resource named `<script>…` must render inert; this
is a test).

## 6. Determinism

Given equal `Assessment` objects and equal flags, all three renderers produce byte-identical
output. No timestamps (unless explicitly injected), no locale-dependent formatting, no
environment reads.

## 7. Acceptance criteria

1. **Golden files:** a fixture `Assessment` (built in code, covering ≥ 1 finding of every
   severity, ≥ 1 unknown, all four control statuses, a not-applicable rule) renders to
   `tests/fixtures/reports/expected.md` / `.html` / `.json` byte-for-byte.
2. Empty assessment (no findings) renders a report that says so and scores 100 — with the
   disclaimer still present.
3. XSS: node name `<script>alert(1)</script>` appears escaped in HTML output;
   `<script>` never appears unescaped anywhere in the document.
4. `include_passes` golden-file variant includes the passed-checks section.
5. `render_json` without `generated_at` contains no timestamp key; with it, contains exactly
   the given string.
6. Disclaimer text is asserted verbatim in all three formats.
7. Determinism: render the same assessment twice → identical bytes, all formats.
