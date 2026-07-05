"""Three-valued condition evaluation — the exact truth tables of spec 004 §5.

Every condition yields ("pass" | "fail" | "unknown", detail). A property that
is absent or null is *missing*: most operators return "unknown" for it, so the
tool never claims what it does not know (ADR-0004). Details are built from
fixed templates only — deterministic, never free-form.
"""

from __future__ import annotations

import json
import re

from archassessor.graph.model import Graph, Node
from archassessor.rules.schema import Combinator, Condition, Leaf, Related

Verdict = str  # "pass" | "fail" | "unknown"

MAX_MATCHED_STRING = 4096  # threat T3: cap regex subject length (spec 008)


def _fmt(value: object) -> str:
    """Deterministic value rendering: true/false/null/"text"/numbers."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


_EXPECTATIONS = {
    "equals": lambda op: _fmt(op),
    "not_equals": lambda op: f"not {_fmt(op)}",
    "in": lambda op: f"one of {_fmt(op)}",
    "not_in": lambda op: f"none of {_fmt(op)}",
    "gte": lambda op: f"a number >= {op}",
    "lte": lambda op: f"a number <= {op}",
    "contains": lambda op: f"a list containing {_fmt(op)}",
    "not_contains": lambda op: f"a list without {_fmt(op)}",
    "matches": lambda op: f"a match for /{op}/",
}


def _leaf(node: Node, cond: Leaf) -> tuple[Verdict, str]:
    prop, op, operand = cond.property, cond.operator, cond.operand
    value = node.properties.get(prop)
    missing = prop not in node.properties or value is None

    if op == "has_tag_key":
        tags = node.properties.get("tags")
        key = str(operand)
        if isinstance(tags, list) and any(t.startswith(key + "=") for t in tags):
            return "pass", f"tag `{key}` is present"
        return "fail", f"no tag with key `{key}`"

    if op == "exists":
        if bool(operand):
            if missing:
                return "fail", f"`{prop}` is absent (expected present)"
            return "pass", f"`{prop}` is {_fmt(value)} (expected present)"
        if missing:
            return "pass", f"`{prop}` is absent (expected absent)"
        return "fail", f"`{prop}` is {_fmt(value)} (expected absent)"

    if missing:
        return "unknown", f"`{prop}` could not be determined from the source"

    expected = _EXPECTATIONS[op](operand)
    detail = f"`{prop}` is {_fmt(value)} (expected {expected})"

    if op == "equals":
        ok = type(value) is type(operand) and value == operand
    elif op == "not_equals":
        ok = not (type(value) is type(operand) and value == operand)
    elif op == "in":
        ok = value in list(operand)  # type: ignore[call-overload]
    elif op == "not_in":
        ok = value not in list(operand)  # type: ignore[call-overload]
    elif op in {"gte", "lte"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "fail", detail
        ok = value >= operand if op == "gte" else value <= operand  # type: ignore[operator]
    elif op in {"contains", "not_contains"}:
        if not isinstance(value, list):
            return "fail", detail
        ok = (operand in value) if op == "contains" else (operand not in value)
    elif op == "matches":
        if not isinstance(value, str):
            return "fail", detail
        if len(value) > MAX_MATCHED_STRING:
            return "unknown", f"`{prop}` is too long to match safely"
        ok = re.fullmatch(str(operand), value) is not None
    else:  # pragma: no cover - parser guarantees operator validity
        raise ValueError(f"unknown operator {op!r}")

    return ("pass" if ok else "fail"), detail


def _related(node: Node, graph: Graph, cond: Related) -> tuple[Verdict, str]:
    edges = (
        graph.edges_from(node.id, cond.edge_type)
        if cond.direction == "outgoing"
        else graph.edges_to(node.id, cond.edge_type)
    )
    if cond.target_type is not None:
        kept = []
        for edge in edges:
            other_id = edge.to_id if cond.direction == "outgoing" else edge.from_id
            other = graph.node_by_id(other_id)
            if other is not None and other.type == cond.target_type:
                kept.append(edge)
        edges = kept

    target = f" to a `{cond.target_type}` node" if cond.target_type else ""
    if cond.exists:
        if edges:
            return "pass", f"{cond.direction} `{cond.edge_type}` edge{target} is present"
        return "fail", f"no {cond.direction} `{cond.edge_type}` edge{target}"
    if edges:
        return (
            "fail",
            f"found {len(edges)} {cond.direction} `{cond.edge_type}` edge(s){target} (expected none)",
        )
    return "pass", f"no {cond.direction} `{cond.edge_type}` edge{target}, as required"


def _combine(node: Node, graph: Graph, cond: Combinator) -> tuple[Verdict, str]:
    # Evaluate every child (no short-circuit) so details stay stable (spec 004 §5.2).
    outcomes = [evaluate_condition(node, graph, child) for child in cond.children]
    verdicts = [v for v, _ in outcomes]

    if cond.kind == "all":
        verdict = "fail" if "fail" in verdicts else "unknown" if "unknown" in verdicts else "pass"
        deciding = "fail" if verdict == "fail" else "unknown" if verdict == "unknown" else None
    elif cond.kind == "any":
        verdict = "pass" if "pass" in verdicts else "unknown" if "unknown" in verdicts else "fail"
        deciding = "pass" if verdict == "pass" else "unknown" if verdict == "unknown" else None
    else:  # none: pass when every child fails
        verdict = "fail" if "pass" in verdicts else "unknown" if "unknown" in verdicts else "pass"
        deciding = "pass" if verdict == "fail" else "unknown" if verdict == "unknown" else None

    details = [d for v, d in outcomes if deciding is None or v == deciding]
    return verdict, "; ".join(details)


def evaluate_condition(node: Node, graph: Graph, cond: Condition) -> tuple[Verdict, str]:
    """Evaluate one condition against one node; pure, deterministic."""
    if isinstance(cond, Leaf):
        return _leaf(node, cond)
    if isinstance(cond, Related):
        return _related(node, graph, cond)
    return _combine(node, graph, cond)
