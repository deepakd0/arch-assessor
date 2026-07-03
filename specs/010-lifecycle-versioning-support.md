# Spec 010 — Lifecycle, Versioning, Release & Support

**Depends on:** specs 000–009. Defines the promises the project makes about its own evolution.

## 1. Versioning policy

**Semantic versioning**, starting at `0.1.0`. Pre-1.0 semantics, stated honestly in the README:
minor bumps (0.x → 0.y) may break anything *except* the Stable Contracts below; patch bumps
are fixes only. `1.0.0` is declared when the parser survives the corpus suite (spec 009 §6)
for a full quarter without high-severity issues and at least 5 external teams use the tool in CI.

### Stable contracts (never break without a major bump, even pre-1.0)

| Contract | Defined in |
|----------|-----------|
| CLI exit codes 0/1/2/3 and their meanings | 006 §4 |
| Graph JSON `schema_version` semantics (readers reject unknown majors) | 001 §3, 000 §5 |
| Rule YAML `schema_version` semantics | 003 §3 |
| Assessment JSON structure (additive changes only within a major) | 004 §3 |
| Determinism: same inputs + same tool version → identical bytes | 000 §4 |

Determinism is promised **per version** — a new tool version may legitimately change output
(new rules, better parsing); the changelog must say so.

## 2. Deprecation policy

CLI flags, rule fields, and report sections are deprecated before removal: at least one minor
version emitting a stderr deprecation warning naming the replacement, removal no sooner than
the next minor. Rule *ids* in the built-in pack are never reused — a retired rule's id is
tombstoned in the pack changelog (auditors may hold old reports referencing it).

## 3. Rule pack versioning

The built-in pack carries its own version (`packs/builtin: 2026.07`, calendar-versioned) and
changelog, displayed in the report's "About" section. Rule additions/severity changes are
pack changes, not code changes, and follow spec 011 governance. A report is reproducible from
(tool version × pack version × input) — all three are printed in it.

## 4. Release process (checklist, automated where possible)

1. CI green on main (all spec-009 jobs, including determinism and pip-audit).
2. `CHANGELOG.md` updated (Keep-a-Changelog format; user-facing wording).
3. Version bumped in exactly one place (`archassessor/__init__.py`; pyproject reads it).
4. Tag `vX.Y.Z` → CI builds sdist+wheel and publishes to PyPI via **trusted publishing
   (OIDC)** — no long-lived PyPI tokens anywhere (threat T8).
5. GitHub Release with the changelog section; artifacts attached.
6. Post-release smoke test: `pip install archassessor==X.Y.Z` in a clean venv on the CI
   matrix → `archscan scan` on the `simple/` fixture matches expected output.

PyPI account: 2FA from day zero. Package name availability check is a Phase 0 task (both
`archassessor` and the final product name — the working title may not survive trademark
search; renaming after users exist is expensive, so do the search *before* first publish).

## 5. License & open-core boundary

Decision tracked in [ADR-0007](../decisions/0007-license-and-open-core.md) — currently
**proposed: Apache-2.0** for everything in this repo (CLI, engine, formats, built-in pack),
because the CLI is the distribution wedge and Apache-2.0 maximizes enterprise adoption
comfort (explicit patent grant). The intended commercial boundary is *hosted services*
(dashboards, history, evidence workflows, org management — Phase 3), not the local tool.
Consequence to hold firm on: never accept external contributions without a CLA decision
first (Phase 2 gate, before the repo goes public).

## 6. Support model (honest, pre-revenue)

- Channels: GitHub Issues (bugs/features) + `SECURITY.md` private email (vulnerabilities).
- Response targets (stated in README as intentions, not SLAs): security acknowledgment
  ≤ 7 days; bug triage weekly batch (this is a part-time solo project and the README says so
  — users respect honesty and resent silence).
- Supported versions: latest minor only, pre-1.0.
- Issue templates: bug (requires tool version, OS, minimal `.tf` reproducer — *with a warning
  not to paste proprietary infrastructure code*), feature request, parser-coverage gap
  (its own template — this is the Phase 2 prioritization inbox).

## 7. Documentation set (ships with 0.1.0)

README quickstart (install → scan → read report in < 5 min, PRD R-12) · rule-authoring guide
(from spec 003, with 3 worked examples) · report-interpretation guide (what `unknown` means,
what the score is and isn't) · `CHANGELOG.md` · `SECURITY.md` · this specs directory.
Docs live in-repo (no docs site pre-1.0).
