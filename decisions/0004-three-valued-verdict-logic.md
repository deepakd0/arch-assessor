# 0004 — Three-valued verdict logic (pass / fail / unknown)

**Status:** accepted (2026-07-02)

## Context
Static parsing (ADR-0002) guarantees missing data. Binary logic forces a lie in both
directions: default-pass hides real gaps (fatal for a compliance-evidence product);
default-fail buries users in noise and kills trust in week one (PRD signal-quality metric).

## Decision
Kleene three-valued logic throughout the engine (spec 004 §5): missing/null property →
`unknown`, propagated through combinators; unknowns surfaced in a dedicated report section,
count half-weight in the score, and roll up to control status `unknown`, never `satisfied`.

## Consequences
Good: the tool never claims what it doesn't know — the single most important trust property
we have; unknowns become a to-do list that markets Phase 4 (manual model) and Phase 5 (cloud
scan) for us. Bad: every operator needs three truth-table rows (spec 009 demands 100 % branch
coverage on them); rule authors must learn that `unknown ≠ fail`; exit codes ignore unknowns
in v1, which a strict shop may dislike (`--strict-unknown` is Phase 2 backlog).
