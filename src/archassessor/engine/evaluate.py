"""Pure evaluation: graph + rules -> Assessment (spec 004).

No I/O, no clock, no randomness, no globals. Calling evaluate twice with the
same inputs returns equal results and never mutates the inputs — this purity
is a product guarantee (customers gate CI on it), not a style preference.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from archassessor.engine.conditions import Verdict, evaluate_condition
from archassessor.graph.model import Edge, Graph, Node, SourceRef
from archassessor.rules.schema import Rule


class _GraphIndex:
    """O(1) node lookup and precomputed adjacency for bulk evaluation.

    Built once per evaluate() call so relationship rules stay linear in
    graph size (NFR-P5) instead of re-scanning and re-sorting edge lists
    per node. Read-only over the input graph; purity is preserved.
    """

    def __init__(self, graph: Graph) -> None:
        self._by_id: dict[str, Node] = {n.id: n for n in graph.nodes}
        self._out: dict[tuple[str, str], list[Edge]] = {}
        self._in: dict[tuple[str, str], list[Edge]] = {}
        for edge in sorted(graph.edges, key=lambda e: e.id):
            self._out.setdefault((edge.from_id, edge.type), []).append(edge)
            self._in.setdefault((edge.to_id, edge.type), []).append(edge)

    def node_by_id(self, node_id: str) -> Node | None:
        return self._by_id.get(node_id)

    def _select(
        self, table: dict[tuple[str, str], list[Edge]], node_id: str, edge_type: str | None
    ) -> list[Edge]:
        if edge_type is not None:
            return table.get((node_id, edge_type), [])
        merged = [e for (nid, _), edges in table.items() if nid == node_id for e in edges]
        return sorted(merged, key=lambda e: e.id)

    def edges_from(self, node_id: str, edge_type: str | None = None) -> list[Edge]:
        return self._select(self._out, node_id, edge_type)

    def edges_to(self, node_id: str, edge_type: str | None = None) -> list[Edge]:
        return self._select(self._in, node_id, edge_type)


SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")
FAIL_PENALTY = {"critical": 15.0, "high": 10.0, "medium": 5.0, "low": 2.0, "info": 0.0}


@dataclass
class RuleResult:
    rule_id: str
    node_id: str
    verdict: Verdict
    detail: str


@dataclass
class Finding:
    rule_id: str
    rule_title: str
    severity: str
    category: str
    description: str
    node_id: str
    node_name: str
    node_type: str
    verdict: Verdict  # "fail" or "unknown"
    detail: str
    remediation: str
    mappings: dict[str, list[str]]
    source: SourceRef


@dataclass
class FrameworkControlStatus:
    framework: str
    control: str
    status: str  # satisfied | gap | unknown | not_assessed
    rule_ids: list[str]


@dataclass
class Summary:
    nodes_total: int
    rules_evaluated: int
    rules_not_applicable: int
    results_pass: int
    results_fail: int
    results_unknown: int
    findings_by_severity: dict[str, int]
    score: int


@dataclass
class Assessment:
    graph_metadata: dict[str, str]
    results: list[RuleResult]
    findings: list[Finding]
    not_applicable_rule_ids: list[str]
    summary: Summary
    frameworks: list[FrameworkControlStatus]
    schema_version: str = "1.0"


def _subjects(nodes_sorted: list[Node], index: _GraphIndex, rule: Rule) -> list[Node]:
    if rule.match.node_types == ["any"]:
        nodes = nodes_sorted
    else:
        wanted = set(rule.match.node_types)
        nodes = [n for n in nodes_sorted if n.type in wanted]
    if rule.match.where is None:
        return nodes
    # Nodes whose filter is fail or unknown are excluded from subjects (spec 004 §4).
    return [n for n in nodes if evaluate_condition(n, index, rule.match.where)[0] == "pass"]


def _score(findings: list[Finding]) -> int:
    penalty = 0.0
    for finding in findings:
        base = FAIL_PENALTY[finding.severity]
        penalty += base if finding.verdict == "fail" else base / 2.0
    raw = 100.0 - penalty
    rounded = int(raw + 0.5) if raw >= 0 else 0  # round half-up, clamp below
    return max(0, min(100, rounded))


def _severity_rank(severity: str) -> int:
    return SEVERITY_ORDER.index(severity)


def _rollup(
    rules: list[Rule],
    not_applicable: set[str],
    results_by_rule: dict[str, list[RuleResult]],
    external: list[Finding],
) -> list[FrameworkControlStatus]:
    # control -> per-rule worst verdict contributions
    contributions: dict[tuple[str, str], dict[str, str]] = {}

    for rule in rules:
        for framework, controls in sorted(rule.mappings.items()):
            for control in controls:
                key = (framework, control)
                bucket = contributions.setdefault(key, {})
                if rule.id in not_applicable:
                    bucket.setdefault(rule.id, "not_assessed")
                    continue
                verdicts = {r.verdict for r in results_by_rule.get(rule.id, [])}
                if "fail" in verdicts:
                    bucket[rule.id] = "fail"
                elif "unknown" in verdicts:
                    bucket[rule.id] = "unknown"
                else:
                    bucket[rule.id] = "pass"

    for finding in external:
        for framework, controls in sorted(finding.mappings.items()):
            for control in controls:
                bucket = contributions.setdefault((framework, control), {})
                current = bucket.get(finding.rule_id)
                if finding.verdict == "fail" or current is None:
                    bucket[finding.rule_id] = finding.verdict

    statuses: list[FrameworkControlStatus] = []
    for (framework, control), bucket in sorted(contributions.items()):
        verdicts = set(bucket.values())
        if "fail" in verdicts:
            status = "gap"
        elif "unknown" in verdicts:
            status = "unknown"
        elif "pass" in verdicts:
            status = "satisfied"
        else:
            status = "not_assessed"
        statuses.append(
            FrameworkControlStatus(
                framework=framework,
                control=control,
                status=status,
                rule_ids=sorted(bucket),
            )
        )
    return statuses


def evaluate(
    graph: Graph, rules: list[Rule], external_findings: tuple[Finding, ...] = ()
) -> Assessment:
    """Evaluate all rules against the graph; return the complete assessment.

    external_findings is the Phase 2 SARIF extension point (spec 004 §8): they
    join findings, summary counts, score, and the framework rollup exactly
    like native findings.
    """
    results: list[RuleResult] = []
    findings: list[Finding] = list(external_findings)
    not_applicable: list[str] = []
    results_by_rule: dict[str, list[RuleResult]] = {}
    index = _GraphIndex(graph)
    nodes_sorted = sorted(graph.nodes, key=lambda n: n.id)

    for rule in sorted(rules, key=lambda r: r.id):
        subjects = _subjects(nodes_sorted, index, rule)
        if not subjects:
            not_applicable.append(rule.id)
            continue
        for node in subjects:
            verdict, detail = evaluate_condition(node, index, rule.condition)
            result = RuleResult(rule_id=rule.id, node_id=node.id, verdict=verdict, detail=detail)
            results.append(result)
            results_by_rule.setdefault(rule.id, []).append(result)
            if verdict in {"fail", "unknown"}:
                findings.append(
                    Finding(
                        rule_id=rule.id,
                        rule_title=rule.title,
                        severity=rule.severity,
                        category=rule.category,
                        description=rule.description,
                        node_id=node.id,
                        node_name=node.name,
                        node_type=node.type,
                        verdict=verdict,
                        detail=detail,
                        remediation=rule.remediation,
                        mappings=rule.mappings,
                        source=node.source,
                    )
                )

    results.sort(key=lambda r: (r.rule_id, r.node_id))
    findings.sort(key=lambda f: (_severity_rank(f.severity), f.rule_id, f.node_id))
    not_applicable.sort()

    by_severity = dict.fromkeys(SEVERITY_ORDER, 0)
    for finding in findings:
        by_severity[finding.severity] += 1

    summary = Summary(
        nodes_total=len(graph.nodes),
        rules_evaluated=len(rules) - len(not_applicable),
        rules_not_applicable=len(not_applicable),
        results_pass=sum(1 for r in results if r.verdict == "pass"),
        results_fail=sum(1 for r in results if r.verdict == "fail"),
        results_unknown=sum(1 for r in results if r.verdict == "unknown"),
        findings_by_severity=by_severity,
        score=_score(findings),
    )
    frameworks = _rollup(
        sorted(rules, key=lambda r: r.id),
        set(not_applicable),
        results_by_rule,
        list(external_findings),
    )
    return Assessment(
        graph_metadata=dict(graph.metadata),
        results=results,
        findings=findings,
        not_applicable_rule_ids=not_applicable,
        summary=summary,
        frameworks=frameworks,
    )


def _finding_payload(finding: Finding) -> dict[str, object]:
    source: dict[str, object] = {"ingestor": finding.source.ingestor}
    if finding.source.file is not None:
        source["file"] = finding.source.file
    if finding.source.line is not None:
        source["line"] = finding.source.line
    return {
        "rule_id": finding.rule_id,
        "rule_title": finding.rule_title,
        "severity": finding.severity,
        "category": finding.category,
        "description": finding.description,
        "node_id": finding.node_id,
        "node_name": finding.node_name,
        "node_type": finding.node_type,
        "verdict": finding.verdict,
        "detail": finding.detail,
        "remediation": finding.remediation,
        "mappings": {k: list(v) for k, v in sorted(finding.mappings.items())},
        "source": source,
    }


def assessment_to_json(assessment: Assessment) -> str:
    """Canonical JSON: sorted keys, 2-space indent, trailing newline."""
    payload = {
        "schema_version": assessment.schema_version,
        "graph_metadata": assessment.graph_metadata,
        "summary": {
            "nodes_total": assessment.summary.nodes_total,
            "rules_evaluated": assessment.summary.rules_evaluated,
            "rules_not_applicable": assessment.summary.rules_not_applicable,
            "results_pass": assessment.summary.results_pass,
            "results_fail": assessment.summary.results_fail,
            "results_unknown": assessment.summary.results_unknown,
            "findings_by_severity": assessment.summary.findings_by_severity,
            "score": assessment.summary.score,
        },
        "results": [
            {
                "rule_id": r.rule_id,
                "node_id": r.node_id,
                "verdict": r.verdict,
                "detail": r.detail,
            }
            for r in assessment.results
        ],
        "findings": [_finding_payload(f) for f in assessment.findings],
        "not_applicable_rule_ids": assessment.not_applicable_rule_ids,
        "frameworks": [
            {
                "framework": s.framework,
                "control": s.control,
                "status": s.status,
                "rule_ids": s.rule_ids,
            }
            for s in assessment.frameworks
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
