# 0005 — argparse + hand-rolled rendering; no click/typer/Jinja2

**Status:** accepted (2026-07-02)

## Context
Two independent library choices came up together during spec 006/005 design. CLI framework:
stdlib `argparse` vs. `click`/`typer` (nicer ergonomics, prettier `--help`, but a runtime
dependency each). Report rendering: hand-built f-string templates vs. `Jinja2` (industry
standard templating, but a runtime dependency, and its auto-escaping defaults are easy to
get wrong for the one output — HTML — that actually needs escaping, spec 008 T5).

## Decision
`argparse` for the CLI; direct Python string building (with `html.escape` applied explicitly
at every interpolation site, spec 005 §5) for all three report formats. No templating engine.

## Consequences
Good: stays inside the ≤ 3 runtime-dependency budget (NFR-M3) for something that isn't core
value; `argparse`'s verbosity is irrelevant at 3 subcommands (spec 006 §3); explicit
`html.escape` calls are individually testable (spec 009 §4 T5) rather than trusting a
framework's global escaping mode. Bad: `--help` output is plainer than `click` would give;
adding a fourth subcommand or a much richer HTML report later may justify revisiting this —
if so, that's a new ADR, not a silent reversal.
