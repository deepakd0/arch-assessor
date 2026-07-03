# 0008 — Ingest scanner output (SARIF); never build scanners

**Status:** accepted (2026-07-02)

## Context
"Security scanning" (CVEs, secrets, SAST, container misconfigurations) is a mature, heavily
resourced market (Snyk, Trivy, Semgrep, Grype — hundreds of engineers of prior art each).
Building competing scanners in-house would mean permanent maintenance treadmills (new CVE
feeds, new secret patterns, new language support) directly competing with free, mature tools,
for a capability that is not this product's differentiator.

## Decision
Never build vulnerability/secret/SAST scanners. Ingest their **SARIF** output (the standard
most of them already export) as `external_findings` into the evaluation engine (spec 004
§8), attach findings to the architecture graph they concern, and roll them up to the same
compliance controls the native rules use. This is the "single pane of glass" value-add: not
the scan itself, but exposure + blast-radius + control-mapping context around someone else's
scan result.

## Consequences
Good: weeks of integration work instead of years of scanner-building; plays well with tools
customers already run rather than asking them to rip anything out; the engine's extension
point (spec 004 §8) was built in Phase 1 specifically so this slots in during Phase 2 without
re-architecting. Bad: quality of security findings is bounded by whichever upstream scanner
the customer chooses to run — we own the aggregation and context, not the detection
accuracy; SARIF's coverage of "architecture-level" concerns is limited, so this remains a
complement to the native rule engine, never a replacement for it.
