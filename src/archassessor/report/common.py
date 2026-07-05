"""Shared report constants and helpers.

DISCLAIMER wording is legally load-bearing (spec 000 §6): reports provide
readiness evidence, never certification. Do not edit without reading spec 011.
"""

from __future__ import annotations

from archassessor.engine.evaluate import Assessment, Finding

DISCLAIMER = (
    "This report is an automated readiness assessment. It provides evidence and gap "
    "analysis against the configured rules and framework mappings. It does not "
    "certify or guarantee compliance with any framework or regulation."
)

SCORE_FORMULA = (
    "100 minus severity-weighted penalties: critical 15, high 10, medium 5, low 2; "
    "unknowns count half"
)

FRAMEWORK_NAMES = {
    "soc2": "SOC 2",
    "iso27001": "ISO 27001",
    "pci_dss": "PCI-DSS",
    "hipaa": "HIPAA",
    "gdpr": "GDPR",
}

STATUS_LABELS = {
    "gap": "⚠ gap",
    "satisfied": "✓ satisfied*",
    "unknown": "? unknown",
    "not_assessed": "– not assessed",
}

SEVERITY_SECTIONS = ("critical", "high", "medium", "low", "info")

SATISFIED_FOOTNOTE = "*satisfied = this tool's checks found no gaps in the controls it covers."


def failed_findings(assessment: Assessment) -> list[Finding]:
    return [f for f in assessment.findings if f.verdict == "fail"]


def unknown_findings(assessment: Assessment) -> list[Finding]:
    return [f for f in assessment.findings if f.verdict == "unknown"]


def where_of(finding: Finding) -> str | None:
    if finding.source.file is None:
        return None
    if finding.source.line is None:
        return finding.source.file
    return f"{finding.source.file}:{finding.source.line}"


def framework_impact(finding: Finding) -> str | None:
    if not finding.mappings:
        return None
    parts = [
        f"{FRAMEWORK_NAMES.get(fw, fw)} {', '.join(controls)}"
        for fw, controls in sorted(finding.mappings.items())
    ]
    return "; ".join(parts)


def findings_line(assessment: Assessment) -> str:
    fails = failed_findings(assessment)
    counts = dict.fromkeys(SEVERITY_SECTIONS, 0)
    for finding in fails:
        counts[finding.severity] += 1
    fail_text = ", ".join(f"{counts[s]} {s}" for s in SEVERITY_SECTIONS)
    return f"Findings: {fail_text} | Unknowns: {len(unknown_findings(assessment))}"
