"""Markdown report renderer (spec 005 §4). Deterministic, template-built."""

from __future__ import annotations

from archassessor import __version__
from archassessor.engine.evaluate import Assessment, Finding
from archassessor.report.common import (
    DISCLAIMER,
    FRAMEWORK_NAMES,
    SATISFIED_FOOTNOTE,
    SCORE_FORMULA,
    SEVERITY_SECTIONS,
    STATUS_LABELS,
    failed_findings,
    findings_line,
    framework_impact,
    unknown_findings,
    where_of,
)


def _code(text: str) -> str:
    """Backtick-wrap user-controlled text; strip backticks so it stays inert."""
    return "`" + text.replace("`", "") + "`"


def _finding_block(finding: Finding, unknown: bool) -> list[str]:
    lines = [
        f"#### [{finding.rule_id}] {finding.rule_title} — "
        f"{_code(finding.node_name)} ({finding.node_type})"
    ]
    where = where_of(finding)
    if where is not None:
        lines.append(f"- **Where:** {_code(where)}")
    lines.append(f"- **What:** {finding.detail}")
    if unknown:
        lines.append(
            "- **How to resolve:** provide the missing configuration in source so the "
            "check has data to act on"
        )
    else:
        lines.append(f"- **Why it matters:** {finding.description}")
        lines.append(f"- **Remediation:** {finding.remediation}")
    impact = framework_impact(finding)
    if impact is not None:
        lines.append(f"- **Framework impact:** {impact}")
    lines.append("")
    return lines


def render_markdown(assessment: Assessment, *, include_passes: bool = False) -> str:
    summary = assessment.summary
    out: list[str] = [
        "# Architecture Assessment Report",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Summary",
        f"- **Score: {summary.score} / 100**  ({SCORE_FORMULA})",
        f"- Nodes assessed: {summary.nodes_total} | Rules evaluated: "
        f"{summary.rules_evaluated} | Not applicable: {summary.rules_not_applicable}",
        f"- {findings_line(assessment)}",
        "",
        "## Findings",
    ]

    fails = failed_findings(assessment)
    if not fails:
        out += ["", "No failed checks."]
    for severity in SEVERITY_SECTIONS:
        section = [f for f in fails if f.severity == severity]
        if not section:
            continue
        out += ["", f"### {severity.capitalize()}"]
        for finding in section:
            out += _finding_block(finding, unknown=False)

    out += ["", "### Needs data (unknown)"]
    unknowns = unknown_findings(assessment)
    if unknowns:
        out.append("")
        for finding in unknowns:
            out += _finding_block(finding, unknown=True)
    else:
        out += ["", "No unknowns — every evaluated check had the data it needed.", ""]

    out += ["## Compliance readiness", ""]
    frameworks = sorted({s.framework for s in assessment.frameworks})
    if not frameworks:
        out += ["No framework mappings among the evaluated rules.", ""]
    for framework in frameworks:
        out += [
            f"### {FRAMEWORK_NAMES.get(framework, framework)}",
            "",
            "| Control | Status | Checked by |",
            "|---------|--------|------------|",
        ]
        for status in assessment.frameworks:
            if status.framework != framework:
                continue
            out.append(
                f"| {status.control} | {STATUS_LABELS[status.status]} | "
                f"{', '.join(status.rule_ids)} |"
            )
        out += ["", SATISFIED_FOOTNOTE, ""]

    out += ["## Rules not applicable to this architecture", ""]
    out.append(
        ", ".join(assessment.not_applicable_rule_ids)
        if assessment.not_applicable_rule_ids
        else "None — every loaded rule found at least one subject."
    )
    out.append("")

    if include_passes:
        out += ["## Passed checks", ""]
        passes = [r for r in assessment.results if r.verdict == "pass"]
        if passes:
            out += [f"- {r.rule_id} — {_code(r.node_id)}" for r in passes]
        else:
            out.append("None.")
        out.append("")

    metadata = assessment.graph_metadata
    out += [
        "## About this assessment",
        "",
        f"- Tool: archscan {__version__}",
        f"- Rules loaded: {summary.rules_evaluated + summary.rules_not_applicable}",
        f"- Graph source: {metadata.get('ingestor', 'unknown')} "
        f"({metadata.get('source_root', 'unknown')})",
        f"- Score formula: {SCORE_FORMULA}",
        "",
    ]
    return "\n".join(out)
