# Built-in Pack — Framework Mapping Reviews

This is the sign-off ledger required by [spec 011 §7](../../../../specs/011-rule-pack-governance.md).
Every `mappings:` entry in the built-in pack is recorded here with its review status.

> [!WARNING]
> **The reviews below are a TECHNICAL PRE-REVIEW by the tooling, not an auditor
> sign-off.** They verify that (a) each referenced control identifier is real and
> (b) the mapping is technically plausible. They are **not** performed by a
> qualified compliance SME and **must not** be presented to an auditor, a
> customer, or in marketing as evidence of compliance until a human SME with
> audit experience for the relevant framework confirms each mapping and signs the
> "SME" column below.
>
> Per spec 011 §7, before any public `0.1.0` release the maintainer must either
> obtain that SME sign-off **or strip the mappings** (an unmapped pack is
> acceptable; an unsigned mapping is not). This ledger exists to make that human
> review fast, not to substitute for it.

## Review legend

- **✅ plausible** — control ID verified real; mapping is a defensible technical fit; awaiting SME confirmation.
- **⚠️ questionable** — control ID is real but the semantic fit is weak or arguable; SME should scrutinise or re-map.
- **SME** — name + date of the qualified human reviewer who confirmed the mapping. Empty = not yet signed off (do not ship as a compliance claim).

## SOC 2 (AICPA Trust Services Criteria)

| Rule | Control | Technical assessment | Status | SME |
|------|---------|----------------------|--------|-----|
| BASE-SEC-001, -002 | CC6.1 | Logical-access protection of stored data via encryption at rest. Strong fit. | ✅ plausible | |
| BASE-SEC-001, -002 | CC6.7 | CC6.7 concerns **transmission, movement, and removal** of information (in-transit / media handling). At-rest encryption fits CC6.1 more cleanly; CC6.7 is arguable only under a broad "protects during removal of storage media" reading. | ⚠️ questionable | |
| BASE-SEC-003, -004, -010, -005, -006, BASE-DATA-001 | CC6.1 | Encryption / key-rotation / non-public data stores — logical-access protection. Strong fit. | ✅ plausible | |
| BASE-SEC-005, -006, -007, -008, -009, -011, BASE-NET-001, -002 | CC6.6 | Boundary protection against external threats (public exposure, open ingress, subnet placement). Strong fit. | ✅ plausible | |
| BASE-OPS-003 | CC7.2 | Access logging supports monitoring components for anomalies. Defensible. | ✅ plausible | |
| BASE-OPS-001, -002 | CC1.3 | CC1.3 concerns organisational **structures, reporting lines, and authorities**. Owner/environment resource tags support accountability only indirectly; this is a weak fit. Consider whether tagging maps better to an operational criterion, or drop the mapping. | ⚠️ questionable | |
| BASE-REL-001, -002, -003, -004 | A1.2 | Availability: backup, recovery infrastructure, redundancy (multi-AZ, retention, deletion protection, versioning). Strong fit. | ✅ plausible | |
| BASE-REL-002 | A1.3 | A1.3 concerns **testing** recovery procedures. Backup *retention* enables recovery but is not recovery testing; this belongs under A1.2. Recommend SME drop A1.3 here. | ⚠️ questionable | |

## ISO 27001:2022 (Annex A)

| Rule | Control | Technical assessment | Status | SME |
|------|---------|----------------------|--------|-----|
| BASE-SEC-001, -002 | A.8.24 | A.8.24 "Use of cryptography" explicitly covers cryptographic protection of **stored data**. Verified against the published control description. Correct fit. | ✅ plausible | |

## PCI-DSS (v4.0)

> Control **text** is copyrighted (spec 011 §5) and is not reproduced here. The
> assessments below are from working knowledge of the standard's structure and
> **carry extra version risk** — PCI requirement numbering shifted between
> v3.2.1 and v4.0. An SME must confirm both the mapping and the target version.

| Rule | Control | Technical assessment | Status | SME |
|------|---------|----------------------|--------|-----|
| BASE-SEC-001 | 3.5.1 | Rendering stored PAN unreadable — encryption at rest is a listed mechanism. Applies only where the database stores cardholder data. Plausible, pending version + applicability confirmation. | ✅ plausible | |
| BASE-SEC-005 | 1.3.1 | Restricting inbound traffic to the cardholder data environment — a publicly reachable database contradicts this. Plausible, pending version confirmation. | ✅ plausible | |

## Open items for the SME reviewer

1. Resolve the three ⚠️ questionable mappings (CC6.7 on at-rest encryption; A1.3 on backup retention; CC1.3 on tagging).
2. Confirm the PCI-DSS target version (the pack does not currently declare one).
3. Sign the SME column for every ✅ mapping to be kept, or instruct which to strip.

Until step 3 is complete for a given control, the compliance-readiness section of
any report **describes tool findings only** and is not an assertion of compliance —
which is exactly what the report's fixed disclaimer already states.
