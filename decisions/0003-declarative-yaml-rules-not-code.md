# 0003 — Rules are declarative YAML, not code plugins or OPA/Rego

**Status:** accepted (2026-07-02)

## Context
Alternatives: Python plugin rules (maximum power; arbitrary code execution from
semi-trusted files — kills threat model T2/T3 story and safe rule-sharing); OPA/Rego
(industry-standard policy language; steep learning curve for the target persona, heavy
dependency, and our graph+three-valued semantics fit it awkwardly); a custom DSL (power
without a parser ecosystem — worst of both).

## Decision
Declarative YAML (`match` + `assert` condition trees, spec 003). Power ceiling is deliberate.
Escape hatches, in order, when the ceiling binds: add an operator (like `has_tag_key`),
add a condition type (like `related`), and only then — Phase 2+, own ADR — sandboxed plugins.

## Consequences
Good: rules are data — safe to load, diff, review, and ship from untrusted-ish sources;
a platform engineer writes one in minutes; load-time validation catches most authoring errors.
Bad: some real rules (multi-hop graph reasoning, e.g. BASE-NET-003) can't be expressed yet
and must be documented as limitations. Risk accepted: condition-language creep — every new
operator needs truth-table rows, tests, and docs, which is friction by design.
