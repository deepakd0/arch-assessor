# Spec 011 — Rule Pack & Framework-Mapping Governance

**Depends on:** specs 003, 010. Defines the human process that keeps rule content and
compliance mappings trustworthy. This is a process spec — its "implementation" is checklists,
templates, and review discipline, not code.

## 1. Why this exists

A wrong *rule* produces a false finding — annoying, self-correcting (users see the code and
push back). A wrong *framework mapping* produces false compliance evidence — invisible to the
user, discovered by their auditor, and fatal to the product's credibility. Mappings therefore
get a stricter process than code.

## 2. Roles

| Role | Who (Phase 1 reality) | Authority |
|------|----------------------|-----------|
| Rule author | Founder / contributor | Drafts rules and proposed mappings |
| Technical reviewer | Founder (self-review checklist until a second engineer exists) | Correctness of match/assert logic against specs 003/004 |
| **Mapping reviewer (SME)** | A person with real audit-side experience of the framework (has been through ≥ 1 audit on the relevant side). Phase 1: recruit 1–2 advisors — a friendly SOC 2 auditor or a compliance lead from Phase 0 interviews; a few hours/quarter, advisory equity or hourly | Every `mappings:` entry requires SME sign-off before shipping. **No SME available = ship the rule without the mapping.** An unmapped good rule is fine; a mismapped rule is not. |

## 3. Rule lifecycle

`draft → technical review → (if mappings) SME review → shipped → (maybe) tombstoned`

Every new/changed rule PR must include:
1. The rule YAML, passing `archscan rules list` validation.
2. A fixture pair: one graph that passes, one that fails, one that yields `unknown` (added to
   the pack's test file).
3. **Mapping justification** (PR description, one per control id): the control's *paraphrased*
   requirement (see §5), why this rule is evidence for it, and the SME sign-off record
   (name + date). Template in `.github/PULL_REQUEST_TEMPLATE/rule.md`.
4. Severity justification in one sentence (severity inflation is drift; `critical` is
   reserved for internet-exposure and data-loss classes).

Changed mappings on an *existing* rule are treated as new mappings (full SME review) and
noted in the pack changelog — downstream users may be citing the old mapping to auditors.

## 4. Quarterly pack review

Once per quarter (calendar-versioned packs, spec 010 §3): re-check mappings against framework
revisions (SOC 2 TSC and ISO texts do get updated); review accumulated user pushback on
findings ("noise" reports from spec 010 §6 issues); retire or re-severity rules with
documented reasoning. Output: new pack version + changelog entry, even if empty ("reviewed
2026-Q4, no changes").

## 5. Framework text licensing (do not skip)

AICPA Trust Services Criteria, ISO/IEC 27001, and PCI-DSS documents are **copyrighted**.
Hard rules for everything this project ships (rules, docs, reports, marketing):

- Control **identifiers** (CC6.1, A.8.24, 3.5.1) — fine to use.
- Control **text** — never reproduced verbatim. Rule descriptions and mapping justifications
  paraphrase in our own words.
- ISO 27001 specifics come from the author's/SME's licensed copy — never scraped summaries
  of it.
- PCI-DSS documents are publicly downloadable but still license-bound — same paraphrase rule.

A pre-ship grep-based check for suspiciously long matches against known control-text phrases
is backlog; until then this is a review-checklist item.

## 6. Custom-rule users (guidance we ship, not enforcement)

The rule-authoring guide (spec 010 §7) tells organisations writing their own packs: use your
own id prefix (never `BASE-`); your mappings are your compliance team's responsibility — the
tool validates *syntax*, only humans validate *meaning*; and put your packs in version
control next to your IaC so rule changes get the same review as infrastructure changes.

## 7. Phase 1 acceptance

- PR template for rules exists with the §3 checklist.
- Built-in pack ships with: every mapping either SME-signed (record kept in
  `packs/builtin/MAPPING-REVIEWS.md` — control id, rule id, reviewer, date) or **removed**
  before 0.1.0 publishes. It is explicitly acceptable for 0.1.0 to ship with few or zero
  mappings if SME recruitment lags — the readiness section simply renders empty. (This is
  the honest-product principle applied to ourselves.)
- README's compliance section links to this governance doc — the process itself is a trust
  signal worth showing.
