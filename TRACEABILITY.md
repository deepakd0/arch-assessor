# Requirements Traceability Matrix

Links every product requirement ([PRD.md](PRD.md) §5) to the spec sections that design it and
the tests that prove it. A requirement with an empty Tests cell is not done, whatever the
code looks like. Update this file in the same PR as any change to a requirement, spec, or
acceptance test — a stale matrix is worse than none.

Test references use the spec's numbered acceptance criteria (e.g. `AT-004.5` = spec 004,
acceptance criterion 5) until real test files exist; when implementing, replace each with the
pytest node id (e.g. `tests/test_engine.py::test_score_formula`).

| Req | Requirement (short) | Designed in | Proven by |
|-----|--------------------|-------------|-----------|
| R-01 | Offline Terraform parsing | 002 all; 008 T1/T4 | AT-002.1–8; AT-009 §4 T1, T4; NFR-C3 socket test |
| R-02 | Canonical versioned graph | 001 all; 000 §5 | AT-001.1–6; property tests 009 §3.1–2 |
| R-03 | Declarative YAML rules | 003 §3–6; 008 T2/T10 | AT-003.1–7; abuse tests T2, T10 |
| R-04 | Built-in SOC 2-mapped pack (≥ 25 rules) | 003 §7; 011 §3, §7 | AT-003.8; pack checks 003 §7; MAPPING-REVIEWS.md record |
| R-05 | Three-valued verdicts | 003 §5; 004 §5 | AT-004.1–4; 009 §2 (100 % branch on conditions.py); property 009 §3.3–4 |
| R-06 | Explainable 0–100 score | 004 §5.5; 005 §4 | AT-004.5; AT-005.1 (formula footnote in golden files) |
| R-07 | Framework readiness rollup | 004 §7; 005 §4; 011 | AT-004.6; AT-005.1 (all four statuses in golden) |
| R-08 | MD/HTML/JSON reports, equal content | 005 all | AT-005.1–7 |
| R-09 | Stable CI exit codes + `--fail-on` | 006 §4; 010 §1 | AT-006.3–6; contract listed in 010 stable-contracts table |
| R-10 | Byte-determinism | 000 §4; 001 §4; 004 §6; 005 §6 | AT-001.3; AT-002.8; AT-004.7; AT-005.7; CI determinism job 009 §7.6 |
| R-11 | No network / no telemetry | 007 NFR-C3, NFR-O3; 008 T9 | no-socket monkeypatch test; source review checklist |
| R-12 | 5-minute zero-config first run | 006 §3.1, §5; 007 NFR-U1/P4; 010 §7 | AT-006.1; NFR-P4 test; usability sessions (PRD §6, manual) |

## Cross-cutting quality attributes → gates

| Attribute | Gate |
|-----------|------|
| Security mitigations (T1–T10) | one abuse test per threat id (009 §4) — CI-blocking |
| Performance (NFR-P1–P5) | benchmark suite (009 §5) — CI-blocking on Linux |
| Portability (NFR-C2) | full suite on ubuntu/macos/windows (009 §7.2) |
| Accessibility (NFR-A1–A4) | structural test + golden-file review checklist |
| Mapping correctness | human gate: SME sign-off per 011 §3 — not automatable, deliberately |

## Known untraced items (accepted gaps, Phase 1)

- PRD success metrics (§6) are measured manually — no product instrumentation by design (R-11).
- NFR-U4 (reading level) and 011 §5 (framework-text licensing) are review-checklist items,
  not tests.
