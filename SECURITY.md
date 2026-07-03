# Security Policy

## Reporting vulnerabilities

**Do not** open a public GitHub issue for security vulnerabilities. Instead, email **security@example.com** with:

- Description of the vulnerability
- Affected version (or "main branch")
- Reproduction steps (if possible)
- Impact assessment
- Suggested fix (if you have one)

**Response target:** we'll acknowledge receipt within 7 days and provide a status update within 14 days.

**Disclosure:** vulnerabilities will be coordinated; we'll request a reasonable embargo period before public disclosure so users have time to patch.

## Threat model

This project is security-adjacent: it reads arbitrary Terraform files and produces evidence for compliance audits. Threat model and mitigations are in [specs/008-threat-model.md](specs/008-threat-model.md).

Key threats addressed:

- **T1**: Parser resource exhaustion (DoS) — capped file sizes, depth limits.
- **T2**: Code execution via YAML — `yaml.safe_load` only, never `yaml.load`.
- **T3**: ReDoS in rule regexes — pattern length limits, timeout guards.
- **T4**: Path traversal — symlink handling, directory walk safety.
- **T5**: XSS in HTML reports — `html.escape` on every user-controlled interpolation.
- **T6–T10**: Tampering, supply chain, verdict spoofing — see spec 008 for full table.

## Dependencies

Runtime dependencies are strictly limited (≤ 3, see spec 007 NFR-M3):

- `python-hcl2` — HCL parsing (pinned exact version).
- `pyyaml` — YAML parsing (pinned exact version, `safe_load` enforced).

**Audit policy:** after every dependency change:

```bash
pip-audit -r requirements.txt --no-deps --disable-pip
```

Zero CVEs — non-negotiable. If a dep has a vulnerability, we patch or replace it immediately.

## Supply chain security

- **PyPI publishing:** OIDC (trusted publishing from GitHub Actions), no long-lived tokens.
- **2FA:** required on PyPI account from day one.
- **Release checklist:** see [specs/010-lifecycle-versioning-support.md](specs/010-lifecycle-versioning-support.md) §4.
- **Signed commits:** optional per contributor, not required.

## Testing

Security testing is built into the test suite (spec 009 §4):

- One test per threat (T1–T10).
- Hostile fixtures in `tests/fixtures/hostile/`.
- Fuzz testing via property-based tests.
- No-socket monkeypatch to enforce offline constraint (spec 008 T9).

Run all security tests: `pytest tests/test_hostile.py -v`

## Disclosure history

*None yet — this is specification phase, no code is implemented.*

---

**Status:** Specification phase, 2026-07-03 · No vulnerabilities reported yet
