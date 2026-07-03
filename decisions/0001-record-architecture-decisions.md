# 0001 — Record architecture decisions

**Status:** accepted (2026-07-02)

## Context
Solo, part-time, AI-assisted project: decisions are made quickly and context evaporates
between sessions. Contributors (human or model) will re-litigate unstated choices.

## Decision
Keep ADRs in `decisions/`, per the format in [README.md](README.md). New runtime
dependencies, format changes, and stable-contract changes *require* one.

## Consequences
Small writing tax per decision; in exchange, "why not X?" has a permanent answer, and AI
assistants building from the specs can be pointed at binding constraints instead of
re-deriving (or violating) them.
