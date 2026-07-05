# ArchAssessor (working title)

A deterministic architecture assessment and validation platform. Point it at what an
organisation actually has (Terraform today; documents, cloud accounts, and a modeling DSL
later) and get a scored assessment against architecture guidelines, governance rules, and
compliance frameworks (SOC 2, ISO 27001, PCI-DSS, HIPAA/GDPR) — plus findings, remediation
guidance, and auditor-friendly evidence.

**Status: Phase 1 core implemented and tested** — the `archscan` CLI works end-to-end
(Terraform → graph → 20-rule SOC 2-mapped assessment → MD/HTML/JSON report; 104 tests,
zero-CVE deps, byte-determinism verified). See
**[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)** for exactly what is ~~done~~ vs.
still open — that file is the hand-off list for continuing the work.

```bash
python3.13 -m venv venv && ./venv/bin/pip install -e .
./venv/bin/archscan scan your-terraform-dir/
```

**👉 [Start with GETTING_STARTED.md](GETTING_STARTED.md)** — quick setup, how to view the guide, and what's next.

Or jump straight to:
- **[PRD.md](PRD.md)** for the why (problem, personas, success metrics)
- **[specs/000-overview.md](specs/000-overview.md)** for the how (implementation guide)
- **[GUIDE.html](GUIDE.html)** for a visual map of the whole document set (open in browser)
- **[CONTRIBUTING.md](CONTRIBUTING.md)** if you want to implement Phase 1

## The one-sentence pitch

> Well-Architected-style assessment, but against *your own rules*, run automatically
> against what you *actually have*.

## Who it's for

Mid-size tech companies (roughly 200–2000 people): teams with platform/staff engineers but
no formal Enterprise Architecture function. Too small for LeanIX/Ardoq, too complex for a
Confluence template and a quarterly review meeting.

## Core design principles

1. **One canonical model.** Every ingestion source (Terraform, docs, DSL, cloud APIs)
   normalizes into a single **architecture graph**. Rules evaluate the graph. Reports and
   diagrams render from the graph. Adding an ingestion source is a connector, never a rewrite.
2. **Deterministic core.** Same graph + same rules = same findings, byte-for-byte, every
   run. No LLM calls anywhere in ingestion→evaluation→report. (LLMs may later assist at the
   *edges* — extracting architecture from messy documents, drafting remediation prose — but
   never inside the validation path.)
3. **Rules are content, mappings are leverage.** Rules ship with framework mappings
   (SOC 2 / ISO 27001 / PCI-DSS / …) so one finding doubles as compliance evidence. Write a
   rule once; it serves every framework it maps to.
4. **Don't build scanners; ingest them.** CVE/secrets/SAST findings come in via SARIF from
   tools users already run (Trivy, Checkov, Semgrep, …). Our value-add is attaching those
   findings to the architecture graph and rolling them up to controls.
5. **Trust by construction.** Everything read-only. The CLI runs locally and sends nothing
   anywhere. Wording discipline: this tool produces *compliance readiness assessments and
   evidence* — it never "certifies compliance." That word never appears in output or marketing.

## Roadmap

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 | Validation: 10–15 customer interviews + Terraform→graph spike | in progress |
| 1 | **Core**: graph schema, Terraform parser, rules engine, SOC 2-mapped rule pack, report renderer, free local CLI | **core implemented — see [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)** |
| 2 | Custom org guardrails, CI enforcement (GitHub Action, exit codes), SARIF importer | planned |
| 3 | Hosted web platform, document ingestion (LLM-assisted extraction + human confirm), per-framework readiness dashboards, evidence export, ISO 27001 pack | planned |
| 4 | Manual modeling DSL, living architecture documentation generation (C4-style diagrams from the graph), PCI-DSS pack | planned |
| 5 | Read-only cloud scanning (AWS first), intended-vs-actual drift detection, HIPAA/GDPR technical-subset packs | planned |
| 6 | Design creation assistant: propose guardrail-compliant designs from requirements | planned |

## Document set

Four kinds of document, each answering a different question. Start at whichever matches
what you need:

| Document | Answers | Audience |
|----------|---------|----------|
| [PRD.md](PRD.md) | Why are we building this, for whom, and how will we know it worked? | founder, future PM |
| `specs/001`–`006` | What exactly gets built, box by box? (implementation specs) | implementer (human or model) |
| `specs/007`–`011` | What quality bar, security posture, test rigor, and process does "production grade" require? | implementer, reviewer |
| [TRACEABILITY.md](TRACEABILITY.md) | Which requirement is proven by which test? | reviewer, auditor |
| [decisions/](decisions/README.md) | Why this choice and not the obvious alternative? | anyone about to re-litigate a decision |

## Phase 1 implementation specifications

Implement in this order — each spec depends only on the ones before it (see
[specs/000 §7](specs/000-overview.md) for the beginner-friendly build order, which differs
from this numbering):

| # | Spec | What it produces |
|---|------|------------------|
| 000 | [Overview & conventions](specs/000-overview.md) | Read this first. Glossary, repo layout, coding standards, how the pieces fit. |
| 001 | [Architecture graph schema](specs/001-architecture-graph-schema.md) | The canonical JSON graph model + Python dataclasses + validation. |
| 002 | [Terraform parser](specs/002-terraform-parser.md) | `.tf` files → architecture graph. |
| 003 | [Rule format & framework mappings](specs/003-rule-format-and-framework-mappings.md) | YAML rule schema, condition language, starter rule pack (~30 rules, SOC 2-mapped). |
| 004 | [Evaluation engine](specs/004-evaluation-engine.md) | Pure function: graph + rules → findings, score, framework rollup. |
| 005 | [Report renderer](specs/005-report-renderer.md) | Findings → Markdown / HTML / JSON reports. |
| 006 | [CLI](specs/006-cli.md) | `archscan` — ties everything together; the free distribution wedge. |

## Production-readiness specifications

Cross-cutting requirements that apply across every spec above — what separates a working
prototype from something you'd trust with a customer's infrastructure and compliance posture:

| # | Spec | What it covers |
|---|------|-----------------|
| 007 | [Non-functional requirements](specs/007-nonfunctional-requirements.md) | Performance/capacity budgets, portability, reliability, usability, accessibility, i18n stance, observability, maintainability gates. |
| 008 | [Threat model](specs/008-threat-model.md) | Assets, trust boundaries, 10 identified threats (DoS, code execution via YAML, ReDoS, path traversal, XSS, supply chain) and their required mitigations. |
| 009 | [Test strategy](specs/009-test-strategy.md) | Coverage gates, property-based tests, the abuse/fuzz suite (one test per threat), benchmarks, real-world corpus testing, full CI pipeline. |
| 010 | [Lifecycle, versioning & support](specs/010-lifecycle-versioning-support.md) | SemVer policy, stable contracts that never break, deprecation policy, release checklist, license, support model. |
| 011 | [Rule pack governance](specs/011-rule-pack-governance.md) | Who reviews compliance mappings before they ship, framework-text licensing rules, quarterly review process. |

## Tech baseline

Python 3.13+, dependencies pinned in `requirements.txt`, zero-CVE policy
(`pip-audit -r requirements.txt --no-deps --disable-pip` after every dependency change),
`pytest` for tests, UTF-8 everywhere, trailing newline in all files.
