# 0006 — Byte-determinism as a product guarantee

**Status:** accepted (2026-07-02)

## Context
Every layer (graph, engine, reports) could have been built "mostly deterministic" — sorted
where convenient, timestamped where convenient. The product's CI use case (spec 006 §4,
PRD US-3/US-4) and its trust story (customers diffing assessments over time, gating merges)
both depend on something stronger: identical input must yield identical output bytes, not
just identical meaning.

## Decision
Byte-determinism is a explicit, tested product guarantee (spec 000 §4), not an implementation
detail: fixed sort keys everywhere output is emitted, no timestamps in canonical output
(opt-in only via explicit flag, spec 006 §3.1 `--timestamp`), no set iteration or dict-order
reliance, no locale-dependent formatting (spec 007 §6), and a dedicated CI job that scans the
same fixture twice in separate processes with different `PYTHONHASHSEED` and diffs the bytes
(spec 009 §7.6).

## Consequences
Good: users can `diff` two reports and trust every difference is real; CI gating is
reproducible; a security-adjacent product gets a rare, checkable trust claim instead of a
marketing adjective. Bad: this constraint threads through *every* spec (001 §4, 002 §8,
004 §6, 005 §6) and every future feature — the determinism guarantee is per tool-version
(spec 010 §1: a new version may legitimately change output, but must say so in the
changelog), so "same input, same version" is the actual promise, not "same input, forever."
