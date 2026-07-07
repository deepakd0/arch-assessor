<!--
Use this template for PRs that add or change a rule in the builtin pack
(src/archassessor/rules/builtin/*.yaml). Select it via the "template" query
param when opening the PR, or copy its checklist into the PR description.
See specs/011-rule-pack-governance.md for the full process this checklist
implements.
-->

## Rule(s) in this PR

- id(s):
- pack file(s):

## Fixtures (spec 011 §3 item 2)

- [ ] A graph fixture where the rule **passes**
- [ ] A graph fixture where the rule **fails**
- [ ] A graph fixture where the rule is **unknown** (missing property)
- [ ] All three added to the rule's test file

## Mapping justification (spec 011 §3 item 3 — one block per framework control)

For each control in this rule's `mappings:`, fill in:

> **Control:** `<framework>` `<control id>`
> **Paraphrased requirement:** (your own words — never copy the framework's
> control text verbatim; see spec 011 §5 on framework-text licensing)
> **Why this rule is evidence for it:**
> **SME reviewer:** (name) — **date:** (yyyy-mm-dd)

**No SME available?** Ship the rule *without* the mapping rather than an
unsigned one (spec 011 §7 — an unmapped rule is fine, an unsigned mapping is
not). Record the sign-off in `src/archassessor/rules/builtin/MAPPING-REVIEWS.md`
once you have it, and open a follow-up PR to add the mapping back.

## Severity justification (spec 011 §3 item 4)

One sentence: why this severity, not one level up or down? (`critical` is
reserved for internet-exposure and data-loss classes — spec 011 §3.)

## Checklist

- [ ] `archscan rules list` validates this rule with no errors
- [ ] Rule id uses this pack's own prefix (never `BASE-` unless this *is* the builtin pack)
- [ ] `description` and `remediation` are non-empty and written for a mid-level engineer
- [ ] No framework control text copied verbatim (paraphrase only)
