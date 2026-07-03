# Product Requirements Document — ArchAssessor Phase 1

**Status:** approved for Phase 1 build · **Owner:** Deepak (founder) · **Last updated:** 2026-07-02

## 1. Problem

Mid-size tech companies (200–2000 people) govern architecture with a Confluence template, a
review meeting, and tribal knowledge. Their architecture standards — encryption, redundancy,
exposure, tagging — are written down somewhere but checked nowhere. When SOC 2 or a customer
security review arrives, engineers spend weeks manually collecting evidence that their
infrastructure matches the standards. Existing tools miss this segment: EA suites
(LeanIX, Ardoq) are priced and shaped for large enterprises; code scanners (Checkov, tfsec)
check individual resources with no concept of architecture-level rules or an organisation's
own guardrails; compliance platforms (Vanta, Drata) automate process evidence but are weak
on architecture-level technical evidence.

## 2. Product vision & Phase 1 slice

**Vision:** the platform where an organisation's architecture guardrails are encoded once,
checked automatically against what actually exists, and double as compliance evidence.

**Phase 1 slice:** a free, local, offline CLI (`archscan`) that assesses a Terraform
repository against a built-in SOC 2-mapped rule pack and produces a scored report. Purpose:
prove the core value loop and earn distribution among platform engineers.

## 3. Personas

| Persona | Role in purchase | Phase 1 relationship |
|---------|------------------|----------------------|
| **Priya — Platform/Staff Engineer** (primary user) | Champion | Runs `archscan` on her repos; shares the report internally. Product must win *her* in 5 minutes. |
| **Sam — Engineering Director** (economic buyer, Phase 3) | Buyer | Reads the HTML report Priya shares; cares about score trend and audit-prep effort saved. |
| **Alex — Compliance/Security Lead** (influencer) | Influencer | Cares about the framework rollup and evidence quality; deeply allergic to overclaiming. |

## 4. User stories (Phase 1)

| ID | Story | Acceptance sketch |
|----|-------|-------------------|
| US-1 | As Priya, I run one command against my Terraform repo and get a readable assessment in under 5 minutes from install, with zero configuration and zero credentials. | `pip install` → `archscan scan infra/` → Markdown report; no flags required. |
| US-2 | As Priya, I can see *why* each finding fired and *how* to fix it, with a file and line number. | Every finding: detail, remediation, `file:line`. |
| US-3 | As Priya, I can trust that a re-run with no changes gives the identical result, so I can diff assessments over time. | Byte-identical output (R-10). |
| US-4 | As Priya, I can put the scan in CI and fail the build on high-severity findings. | Exit-code contract, `--fail-on`, JSON format. |
| US-5 | As Alex, I can see which SOC 2 technical controls have passing evidence, gaps, or insufficient data — worded so it can't be mistaken for certification. | Compliance readiness section + fixed disclaimer. |
| US-6 | As Priya, when the tool can't determine something, it tells me plainly instead of guessing or silently passing. | `unknown` verdicts surfaced in a dedicated report section. |
| US-7 | As Sam, I receive a self-contained HTML report I can open and forward without installing anything. | Single-file HTML, no external assets. |

## 5. Requirements register

Functional (traced in [TRACEABILITY.md](TRACEABILITY.md)):

| ID | Requirement | Spec |
|----|-------------|------|
| R-01 | Parse a Terraform directory fully offline (no terraform binary, credentials, or network) | 002 |
| R-02 | Normalize into a canonical, versioned architecture graph | 001 |
| R-03 | Rules are declarative YAML — users never write code to add a rule | 003 |
| R-04 | Ship a built-in rule pack (≥ 25 rules) with SOC 2 mappings | 003 §7 |
| R-05 | Three-valued verdicts: missing data yields `unknown`, never a false pass/fail | 004 §5 |
| R-06 | Produce an explainable 0–100 score with a printed formula | 004 §5.5 |
| R-07 | Roll findings up to per-framework control readiness statuses | 004 §7 |
| R-08 | Render Markdown, HTML, and JSON reports with identical content | 005 |
| R-09 | Stable CI exit-code contract (0/1/2/3) with `--fail-on` threshold | 006 §4 |
| R-10 | Byte-deterministic outputs for identical inputs | 000 §4, all |
| R-11 | No network calls, no telemetry, no data leaves the machine | 000 §4, 008 |
| R-12 | First useful report within 5 minutes of install, zero config | 006, 007 |

Non-functional requirements live in [specs/007](specs/007-nonfunctional-requirements.md).

## 6. Success metrics

Phase 1 is an instrument-by-hand phase (R-11 forbids telemetry), measured via interviews,
GitHub, and PyPI:

- **Activation:** ≥ 70 % of interviewed pilot users get a report on a real repo on first
  attempt without help. This is the metric; everything else is secondary.
- **Time-to-first-report:** < 5 minutes from `pip install` (timed in usability sessions).
- **Signal quality:** pilot users judge ≥ 80 % of findings on their repo "true and worth
  knowing"; fewer than 1 in 10 findings dismissed as noise.
- **Pull:** ≥ 3 pilot users ask unprompted for custom rules or CI integration (validates
  Phase 2) or for the dashboard (validates Phase 3).
- **Distribution proxy:** 200 GitHub stars / 500 monthly PyPI downloads within 3 months of
  public launch — soft targets, directional only.

## 7. Explicitly out of scope for Phase 1 (and why)

| Cut | Why |
|-----|-----|
| Azure/GCP, remote modules, `count`/`for_each`, tfvars, plan/state ingestion | Coverage breadth is Phase 2 work, prioritized by what pilot users' repos actually break on. |
| Custom rules UX, CI action packaging, SARIF import | Phase 2 — needs Phase 1's pull signal first. |
| Web app, accounts, history, waivers, evidence export | Phase 3 — monetization layer; premature before activation is proven. |
| Diagrams and doc generation | Phase 4 — different value loop. |
| Any LLM feature | LLMs enter only at ingestion edges (Phase 3 doc extraction) — never in validation. |
| Telemetry | Trust is the product. Revisit opt-in telemetry no earlier than Phase 3, as its own decision. |

## 8. Risks & assumptions

| Risk | Type | Mitigation |
|------|------|------------|
| Real-world Terraform is too varied; parser coverage disappoints pilots | product | `unknown` verdicts degrade gracefully; Phase 0 spike on 3 real repos before full build; plan-JSON ingestor is the Phase 2 escape hatch. |
| Findings overlap too much with Checkov/tfsec to feel differentiated | market | Lead with org-guardrails + framework rollup (which they lack); Phase 0 interviews test this exact perception. |
| Control mappings are wrong and damage trust irreparably | product/legal | Governance process in [specs/011](specs/011-rule-pack-governance.md); SME review before any pack ships. |
| Solo part-time capacity stalls mid-build | execution | Specs sized so each is independently completable; build order in 000 §7 front-loads testable-in-isolation pieces. |
| **Assumption:** target segment predominantly uses Terraform on AWS | — | Validate in Phase 0 interviews; if it fails, Phase 2 reprioritizes providers, not the core. |
