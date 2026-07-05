"""Self-contained HTML report (spec 005 §5).

Single file, inline CSS, no JS, no external assets — must open on an
airgapped machine. Every user-controlled value passes through html.escape
(threat T5): node names come from scanned repos and are hostile input.
"""

from __future__ import annotations

from html import escape

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

# Severity color coding (spec 005 §5); severity is never color-only (NFR-A2):
# every use pairs the color with the severity word.
_COLORS = {
    "critical": "#b91c1c",
    "high": "#ea580c",
    "medium": "#d97706",
    "low": "#65a30d",
    "info": "#64748b",
    "unknown": "#64748b",
}

_CSS = """
body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
       max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #1f2937; }
blockquote { border-left: 4px solid #94a3b8; margin: 1rem 0; padding: 0.5rem 1rem;
             color: #475569; background: #f8fafc; }
table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1rem; }
th, td { text-align: left; border-bottom: 1px solid #e2e8f0; padding: 6px 10px; }
.finding { border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px;
           margin: 0 0 12px; }
.sev { font-weight: 700; text-transform: uppercase; font-size: 0.8rem; }
code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; }
.muted { color: #64748b; }
"""


def _finding_card(finding: Finding, unknown: bool) -> str:
    color = _COLORS["unknown" if unknown else finding.severity]
    label = "unknown" if unknown else finding.severity
    rows = [
        f'<div class="finding" style="border-left: 6px solid {color};">',
        f'<span class="sev" style="color: {color};">{escape(label)}</span> ',
        f"<strong>[{escape(finding.rule_id)}] {escape(finding.rule_title)}</strong> — "
        f"<code>{escape(finding.node_name)}</code> ({escape(finding.node_type)})",
        "<ul>",
    ]
    where = where_of(finding)
    if where is not None:
        rows.append(f"<li><strong>Where:</strong> <code>{escape(where)}</code></li>")
    rows.append(f"<li><strong>What:</strong> {escape(finding.detail)}</li>")
    if unknown:
        rows.append(
            "<li><strong>How to resolve:</strong> provide the missing configuration in "
            "source so the check has data to act on</li>"
        )
    else:
        rows.append(f"<li><strong>Why it matters:</strong> {escape(finding.description)}</li>")
        rows.append(f"<li><strong>Remediation:</strong> {escape(finding.remediation)}</li>")
    impact = framework_impact(finding)
    if impact is not None:
        rows.append(f"<li><strong>Framework impact:</strong> {escape(impact)}</li>")
    rows += ["</ul>", "</div>"]
    return "\n".join(rows)


def render_html(assessment: Assessment, *, include_passes: bool = False) -> str:
    summary = assessment.summary
    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8">',
        "<title>Architecture Assessment Report</title>",
        f"<style>{_CSS}</style>",
        "</head>",
        "<body>",
        "<h1>Architecture Assessment Report</h1>",
        f"<blockquote>{escape(DISCLAIMER)}</blockquote>",
        "<h2>Summary</h2>",
        "<ul>",
        f"<li><strong>Score: {summary.score} / 100</strong> "
        f'<span class="muted">({escape(SCORE_FORMULA)})</span></li>',
        f"<li>Nodes assessed: {summary.nodes_total} | Rules evaluated: "
        f"{summary.rules_evaluated} | Not applicable: {summary.rules_not_applicable}</li>",
        f"<li>{escape(findings_line(assessment))}</li>",
        "</ul>",
        "<h2>Findings</h2>",
    ]

    fails = failed_findings(assessment)
    if not fails:
        parts.append("<p>No failed checks.</p>")
    for severity in SEVERITY_SECTIONS:
        section = [f for f in fails if f.severity == severity]
        if not section:
            continue
        parts.append(f"<h3>{escape(severity.capitalize())}</h3>")
        parts.extend(_finding_card(f, unknown=False) for f in section)

    parts.append("<h3>Needs data (unknown)</h3>")
    unknowns = unknown_findings(assessment)
    if unknowns:
        parts.extend(_finding_card(f, unknown=True) for f in unknowns)
    else:
        parts.append("<p>No unknowns — every evaluated check had the data it needed.</p>")

    parts.append("<h2>Compliance readiness</h2>")
    frameworks = sorted({s.framework for s in assessment.frameworks})
    if not frameworks:
        parts.append("<p>No framework mappings among the evaluated rules.</p>")
    for framework in frameworks:
        parts += [
            f"<h3>{escape(FRAMEWORK_NAMES.get(framework, framework))}</h3>",
            "<table>",
            '<tr><th scope="col">Control</th><th scope="col">Status</th>'
            '<th scope="col">Checked by</th></tr>',
        ]
        for status in assessment.frameworks:
            if status.framework != framework:
                continue
            parts.append(
                f"<tr><td>{escape(status.control)}</td>"
                f"<td>{escape(STATUS_LABELS[status.status])}</td>"
                f"<td>{escape(', '.join(status.rule_ids))}</td></tr>"
            )
        parts += ["</table>", f'<p class="muted">{escape(SATISFIED_FOOTNOTE)}</p>']

    parts.append("<h2>Rules not applicable to this architecture</h2>")
    parts.append(
        "<p>"
        + escape(
            ", ".join(assessment.not_applicable_rule_ids)
            if assessment.not_applicable_rule_ids
            else "None — every loaded rule found at least one subject."
        )
        + "</p>"
    )

    if include_passes:
        parts.append("<h2>Passed checks</h2><ul>")
        passes = [r for r in assessment.results if r.verdict == "pass"]
        if passes:
            parts.extend(
                f"<li>{escape(r.rule_id)} — <code>{escape(r.node_id)}</code></li>" for r in passes
            )
        else:
            parts.append("<li>None.</li>")
        parts.append("</ul>")

    metadata = assessment.graph_metadata
    parts += [
        "<h2>About this assessment</h2>",
        "<ul>",
        f"<li>Tool: archscan {escape(__version__)}</li>",
        f"<li>Rules loaded: {summary.rules_evaluated + summary.rules_not_applicable}</li>",
        f"<li>Graph source: {escape(metadata.get('ingestor', 'unknown'))} "
        f"({escape(metadata.get('source_root', 'unknown'))})</li>",
        f"<li>Score formula: {escape(SCORE_FORMULA)}</li>",
        "</ul>",
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(parts)
