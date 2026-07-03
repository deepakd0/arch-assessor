# 0007 — Apache-2.0 + open-core boundary at hosted services

**Status:** proposed (2026-07-02) — confirm before Phase 2 repo goes public

## Context
License choice shapes adoption and the business model simultaneously. MIT is simpler but
lacks an explicit patent grant, which some enterprise legal teams flag during vendor review —
friction directly against the target persona (PRD Alex, the compliance/security lead).
GPL/AGPL would force the hand on any future hosted offering and scares off the exact
mid-size-company adopters this product needs on day one. Fully closed source contradicts the
CLI-as-distribution-wedge strategy (README principle 5, PRD §1) — Terraform/Checkov-style
open-core is the validated playbook in this exact space.

## Decision
License the CLI, engine, formats (graph/rule schemas), and built-in rule pack under
**Apache-2.0**. The commercial boundary sits at *hosted services* introduced in Phase 3
(accounts, history, dashboards, evidence workflows, org management) — never at the local
tool. No repository work accepting outside contributions happens before a CLA decision is
made (tracked as a Phase 2 gate, not yet resolved here).

## Consequences
Good: patent grant removes a common enterprise legal objection; matches the trust-by-
construction principle (nothing hidden in the thing customers run against their
infrastructure); consistent with the proven open-core precedent in this market.
Bad: Apache-2.0 permits a well-funded competitor to fork the CLI and rules and build the
hosted layer faster than a solo founder can — accepted risk, mitigated only by moving first
and by the governance/trust work (spec 011) being hard to fork credibly. **This ADR is
proposed, not accepted** — confirm explicitly before the repository is made public.
