# Spec 007 — Non-Functional Requirements

**Depends on:** spec 000. **Applies to:** every Phase 1 component. Each NFR below is either
enforced by a test, checked in CI, or explicitly marked *documented-only* (a stated stance,
not an automated check).

## 1. Performance & capacity

Reference machine: 4-core laptop, 8 GB RAM, SSD, no network. Measured via `pytest` benchmarks
on generated fixtures (see spec 009 §5).

| ID | Requirement | Target | Enforcement |
|----|-------------|--------|-------------|
| NFR-P1 | End-to-end `archscan scan` on a 1,000-resource repo | < 10 s | benchmark test |
| NFR-P2 | End-to-end scan on a 5,000-resource repo | < 30 s | benchmark test |
| NFR-P3 | Peak memory on a 5,000-resource repo | < 512 MB | benchmark test (`tracemalloc`) |
| NFR-P4 | CLI cold start (`archscan --version`) | < 1 s | test |
| NFR-P5 | Engine cost | O(subjects × rule-condition size); no worse than quadratic in graph size overall | code review + 5k benchmark |

Soft capacity ceilings (beyond them, the tool must still finish or fail cleanly, never hang):
50,000 nodes per graph, 5,000 rules, 10,000 files per repo. Exceeding a ceiling → warning.

## 2. Compatibility & portability

- **NFR-C1:** Python 3.13+; CPython only (documented-only).
- **NFR-C2:** macOS, Linux, Windows — CI matrix runs the full test suite on all three. Use
  `pathlib` throughout; never assume `/` separators or a case-sensitive filesystem; all I/O
  explicit UTF-8 with `newline="\n"` on writes (report bytes must not vary by OS).
- **NFR-C3:** Fully offline. No socket may be opened by any code path — enforced by a test
  that monkeypatches `socket.socket` to raise during a full scan.
- **NFR-C4:** No environment variables read in v1 (removes a whole class of "works on my
  machine"); revisit in Phase 2 config work.

## 3. Reliability & robustness

- **NFR-R1:** No user input (hostile, malformed, enormous) may cause a hang, an unhandled
  traceback, or memory exhaustion within the §1 ceilings. (Threat model, spec 008, defines
  the hostile cases; spec 009 §4 fuzzes them.)
- **NFR-R2:** Partial-input degradation: any subset of parseable files yields an assessment
  of that subset plus warnings — never all-or-nothing (spec 002 W001, spec 006 exit 3 rule).
- **NFR-R3:** Interrupted runs (Ctrl-C) leave no partial `--output` file: write to a temp
  file in the destination directory, then atomic rename.

## 4. Usability

- **NFR-U1:** Zero-config first run (PRD R-12): `archscan scan <dir>` with no other flags
  produces a complete report.
- **NFR-U2:** Error-message standard: every user-facing error names (a) what went wrong,
  (b) which file/flag caused it, (c) one concrete next action. Template:
  `error: <what> (<where>) — <try this>`. Tests assert format for each error class.
- **NFR-U3:** All diagnostics on stderr, report bytes on stdout — never mixed (spec 006 §3.1).
- **NFR-U4:** Reading level: report prose (descriptions, remediations, details) targets a
  mid-level engineer; no unexplained compliance jargon (documented-only, checked in rule-pack
  review, spec 011).

## 5. Accessibility (HTML report)

- **NFR-A1:** Semantic HTML: `<h1>`–`<h3>` hierarchy without skips, `<table>` with `<th scope>`,
  `lang="en"` on `<html>`.
- **NFR-A2:** Severity is never conveyed by color alone — always paired with a text label.
- **NFR-A3:** Text contrast ≥ 4.5:1 against background (WCAG 2.1 AA); verify the spec-005
  palette once and pin it.
- **NFR-A4:** Report is readable with CSS disabled (content order is logical).
  Enforcement: golden-file review checklist + one structural test (headings hierarchy,
  no color-only spans). Full audit tooling is backlog.

## 6. Internationalisation

**Stance (documented-only): English-only product text in v1**, by decision not omission.
However: all *user data* (resource names, tags, file paths) is UTF-8 end-to-end and must
survive non-ASCII content — one test scans a fixture with emoji and CJK resource names.
No locale-dependent formatting anywhere (no `locale` module, no `%x` dates, `str()` of
numbers only) — this is also a determinism requirement.

## 7. Observability (CLI-appropriate)

- **NFR-O1:** `--verbose` / `-v` flag (add to spec 006 §3.1): step-by-step progress on stderr
  — files parsed, rules loaded, timing per stage. Uses stdlib `logging` to stderr; default
  level WARNING, `-v` = INFO, `-vv` = DEBUG.
- **NFR-O2:** No log output may ever reach stdout (would corrupt report bytes) — tested.
- **NFR-O3:** No telemetry, crash reporting, or update checks (PRD §7). Documented in README.

## 8. Maintainability

- **NFR-M1:** Coverage gates per spec 009 (≥ 90 % core, 100 % of condition truth tables).
- **NFR-M2:** `ruff` (lint + format) and `mypy --strict` on `src/` pass in CI; both pinned.
- **NFR-M3:** Runtime dependency budget: ≤ 3 packages (v1 expects exactly two: `python-hcl2`,
  `pyyaml`). Adding a runtime dependency requires an ADR.
