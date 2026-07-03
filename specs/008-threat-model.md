# Spec 008 — Threat Model (Phase 1 CLI)

**Depends on:** specs 000–006. **Review trigger:** re-run this analysis whenever an ingestor,
input format, or output channel is added (SARIF import and the web platform each get their
own threat model before build).

## 1. Why a CLI needs one

`archscan` is a security-adjacent tool that will be pointed at other people's repositories —
including, at consultancies, repositories the operator does not control. Users will run it in
CI with elevated tokens nearby. A vulnerability here is a reputation-ending event for a
product whose pitch is trust. The flip side: Phase 1's architecture (offline, read-only, no
daemon, no accounts) eliminates entire threat classes by construction — this document keeps
them eliminated.

## 2. Assets & security goals

| Asset | Goal |
|-------|------|
| A1. The host machine and CI environment running the scan | Nothing in scanned input may execute code or exhaust resources on it. |
| A2. The customer's architecture data (the repo, the graph, the report) | Never leaves the machine (PRD R-11); report renders hostile content inert. |
| A3. Assessment integrity | No input may silently alter verdicts (a rule that says fail must fail). |
| A4. The supply chain (our package as installed by users) | Users install what we published; our deps are audited. |

## 3. Trust boundaries

| Input | Trust level | Rationale |
|-------|------------|-----------|
| Terraform files under `PATH` | **Untrusted / hostile** | Third-party modules, vendored code, consultant scenarios. |
| Custom rule files (`--rules`) | **Semi-trusted** | Chosen by the operator, but may be copied from the internet; must not gain code execution. |
| Built-in rule pack | Trusted (ships in our package; governed by spec 011) |
| CLI flags | Trusted (operator) |

## 4. Threats & required mitigations

Each mitigation is REQUIRED and has an owner spec and a test (spec 009 §4 fuzz/abuse suite).

| ID | Threat (STRIDE) | Attack | Mitigation | Owner |
|----|-----------------|--------|------------|-------|
| T1 | DoS via parser exhaustion | Enormous or deeply nested `.tf` files; zip-bomb-style generated HCL; module recursion | Per-file size cap 5 MB (over → `W007`, file skipped); parse under §7 NFR ceilings; module depth ≤ 5 (spec 002 §7); total-files ceiling with clean abort | 002 |
| T2 | Code execution via YAML | Rule file with `!!python/object` payloads | `yaml.safe_load` **only**, everywhere, forever. A test greps the codebase for `yaml.load(` and fails if found unsafely; a fixture with a `!!python/object` rule must produce a load error, not execution | 003 |
| T3 | ReDoS via rule `matches` regex | Semi-trusted rule with catastrophic backtracking pattern (`(a+)+$`) run against attacker-controlled property strings from T1-territory `.tf` | Pattern length ≤ 256 (load error); property-string length evaluated against regex capped at 4,096 chars (longer → verdict `unknown` with detail); residual risk documented: rules are operator-chosen | 003, 004 |
| T4 | Filesystem traversal during walk | Symlink inside repo pointing at `/` or `~/.ssh`; symlink cycles | Directory walk does **not** follow symlinked directories; symlinked files outside the resolved root are skipped with `W008`; cycle-safe by construction | 002 |
| T5 | XSS / markup injection in reports | Resource named `<script>…` or `](javascript:…)` markdown | HTML: `html.escape` every interpolation (spec 005 §5, tested). Markdown: backtick-wrap user strings; strip backticks from user content before wrapping | 005 |
| T6 | Tampering via `--output` | Report path pointing at a file the user didn't intend to clobber | Atomic temp-file + rename (NFR-R3); no other guard in v1 — operator-trusted flag; documented | 006 |
| T7 | Supply chain (inbound) | Compromised or vulnerable dependency | ≤ 3 runtime deps (NFR-M3), pinned exact versions, `pip-audit` in CI with zero-CVE gate, hash-pinned lockfile for dev | repo |
| T8 | Supply chain (outbound) | Attacker publishes lookalike/compromised package | PyPI 2FA + trusted publishing (OIDC from CI) from the *first* release; release checklist in spec 010 | 010 |
| T9 | Information disclosure | Reports contain sensitive architecture detail; users share them carelessly | Product behavior: nothing transmitted (NFR-C3 socket test). Human factor: README and report footer note that reports contain sensitive infrastructure details | 005, docs |
| T10 | Verdict spoofing via duplicate rule ids | Custom rule reuses `BASE-SEC-001` to override a built-in with a weaker check | Duplicate ids across *all* loaded sources are a load error (spec 003 §6) — including builtin collisions | 003 |

## 5. Non-threats (v1, by architecture)

Authentication/session attacks (no accounts), network MITM (no network — enforced by test),
multi-tenant data leakage (no server), privilege escalation (runs at invoker's privilege,
needs only read access + one output file). These become real in Phase 3; the web platform
requires a new threat model before a line of it is written.

## 6. Security engineering practices

- Security fixture directory `tests/fixtures/hostile/` — every T-id above has at least one
  hostile fixture and a test asserting the mitigation (spec 009 §4).
- `SECURITY.md` at repo root from first public release: private disclosure email,
  acknowledgment within 7 days, no bounty (yet), supported-versions table.
- Any new input format, dependency, or output channel → update this document first (the PR
  template asks).
