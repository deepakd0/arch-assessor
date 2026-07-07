# Architecture Assessment Report

> This report is an automated readiness assessment. It provides evidence and gap analysis against the configured rules and framework mappings. It does not certify or guarantee compliance with any framework or regulation.

## Summary
- **Score: 63 / 100**  (100 minus severity-weighted penalties: critical 15, high 10, medium 5, low 2; unknowns count half)
- Nodes assessed: 8 | Rules evaluated: 7 | Not applicable: 1
- Findings: 1 critical, 1 high, 1 medium, 1 low, 1 info | Unknowns: 1

## Findings

### Critical
#### [GOLD-SEC-001] Golden rule GOLD-SEC-001 — `a` (storage)
- **Where:** `main.tf:1`
- **What:** `prop` is false (expected true) for GOLD-SEC-001
- **Why it matters:** Why GOLD-SEC-001 matters.
- **Remediation:** Fix GOLD-SEC-001 by setting the property to true.
- **Framework impact:** SOC 2 CC6.1


### High
#### [GOLD-SEC-002] Golden rule GOLD-SEC-002 — `b` (database)
- **Where:** `main.tf:1`
- **What:** `prop` is false (expected true) for GOLD-SEC-002
- **Why it matters:** Why GOLD-SEC-002 matters.
- **Remediation:** Fix GOLD-SEC-002 by setting the property to true.
- **Framework impact:** SOC 2 CC6.6


### Medium
#### [GOLD-SEC-003] Golden rule GOLD-SEC-003 — `c` (kms_key)
- **Where:** `main.tf:1`
- **What:** `prop` is false (expected true) for GOLD-SEC-003
- **Why it matters:** Why GOLD-SEC-003 matters.
- **Remediation:** Fix GOLD-SEC-003 by setting the property to true.
- **Framework impact:** SOC 2 CC6.1


### Low
#### [GOLD-SEC-004] Golden rule GOLD-SEC-004 — `d` (storage)
- **Where:** `main.tf:1`
- **What:** `prop` is false (expected true) for GOLD-SEC-004
- **Why it matters:** Why GOLD-SEC-004 matters.
- **Remediation:** Fix GOLD-SEC-004 by setting the property to true.


### Info
#### [GOLD-NET-001] Golden rule GOLD-NET-001 — `e` (load_balancer)
- **What:** `prop` is false (expected true) for GOLD-NET-001
- **Why it matters:** Why GOLD-NET-001 matters.
- **Remediation:** Fix GOLD-NET-001 by setting the property to true.


### Needs data (unknown)

#### [GOLD-SEC-005] Golden rule GOLD-SEC-005 — `f` (database)
- **Where:** `main.tf:1`
- **What:** `prop` is false (expected true) for GOLD-SEC-005
- **How to resolve:** provide the missing configuration in source so the check has data to act on
- **Framework impact:** SOC 2 CC7.2

## Compliance readiness

### ISO 27001

| Control | Status | Checked by |
|---------|--------|------------|
| A.8.24 | ⚠ gap | GOLD-SEC-001 |

*satisfied = this tool's checks found no gaps in the controls it covers.

### SOC 2

| Control | Status | Checked by |
|---------|--------|------------|
| CC6.1 | ⚠ gap | GOLD-SEC-001, GOLD-SEC-003 |
| CC6.6 | ⚠ gap | GOLD-SEC-002 |
| CC7.2 | ? unknown | GOLD-SEC-005 |
| CC9.9 | – not assessed | GOLD-OPS-999 |
| CC1.1 | ✓ satisfied* | GOLD-SEC-006 |

*satisfied = this tool's checks found no gaps in the controls it covers.

## Rules not applicable to this architecture

GOLD-OPS-999

## About this assessment

- Tool: archscan 0.1.0.dev0
- Rules loaded: 8
- Graph source: golden (fixture)
- Score formula: 100 minus severity-weighted penalties: critical 15, high 10, medium 5, low 2; unknowns count half
