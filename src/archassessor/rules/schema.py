"""Rule and condition data model plus dict -> tree parsing (spec 003 §3–5).

Conditions are declarative data. Parsing collects *all* problems into the
supplied error list instead of failing fast, so the loader can report every
issue in a file at once (spec 003 §6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SEVERITIES: tuple[str, ...] = ("critical", "high", "medium", "low", "info")
CATEGORIES: frozenset[str] = frozenset(
    {"security", "reliability", "cost", "operations", "data", "network"}
)
FRAMEWORK_KEYS: frozenset[str] = frozenset({"soc2", "iso27001", "pci_dss", "hipaa", "gdpr"})

RULE_ID_PATTERN = re.compile(r"^[A-Z]{2,8}-[A-Z]{2,8}-\d{3}$")
MAX_REGEX_LENGTH = 256  # threat T3 (spec 008)

LEAF_OPERATORS: frozenset[str] = frozenset(
    {
        "equals",
        "not_equals",
        "exists",
        "in",
        "not_in",
        "gte",
        "lte",
        "contains",
        "not_contains",
        "matches",
    }
)
COMBINATORS: frozenset[str] = frozenset({"all", "any", "none"})


@dataclass
class Leaf:
    property: str
    operator: str  # one of LEAF_OPERATORS or "has_tag_key"
    operand: object


@dataclass
class Combinator:
    kind: str  # all | any | none
    children: list[Condition]


@dataclass
class Related:
    edge_type: str
    direction: str = "outgoing"
    target_type: str | None = None
    exists: bool = True


Condition = Leaf | Combinator | Related


@dataclass
class Match:
    node_types: list[str]  # ["any"] matches every node
    where: Condition | None = None


@dataclass
class Rule:
    id: str
    title: str
    severity: str
    category: str
    description: str
    remediation: str
    mappings: dict[str, list[str]]
    match: Match
    condition: Condition
    source_file: str = ""


def parse_condition(raw: object, where: str, errors: list[str]) -> Condition | None:
    """Parse one condition dict into a tree; append problems to errors."""
    if not isinstance(raw, dict) or not raw:
        errors.append(f"{where}: condition must be a non-empty mapping")
        return None

    combinator_keys = [k for k in raw if k in COMBINATORS]
    if combinator_keys:
        if len(raw) != 1:
            errors.append(f"{where}: combinator {combinator_keys[0]!r} must be the only key")
            return None
        kind = combinator_keys[0]
        children_raw = raw[kind]
        if not isinstance(children_raw, list) or not children_raw:
            errors.append(f"{where}: {kind!r} requires a non-empty list of conditions")
            return None
        children = [
            parsed
            for i, child in enumerate(children_raw)
            if (parsed := parse_condition(child, f"{where}.{kind}[{i}]", errors)) is not None
        ]
        return (
            Combinator(kind=kind, children=children) if len(children) == len(children_raw) else None
        )

    if "related" in raw:
        if len(raw) != 1:
            errors.append(f"{where}: 'related' must be the only key")
            return None
        body = raw["related"]
        if not isinstance(body, dict):
            errors.append(f"{where}: 'related' must be a mapping")
            return None
        edge_type = body.get("edge_type")
        direction = body.get("direction", "outgoing")
        exists = body.get("exists", True)
        if edge_type not in {"contains", "depends_on", "routes_to"}:
            errors.append(f"{where}: related.edge_type must be contains/depends_on/routes_to")
            return None
        if direction not in {"outgoing", "incoming"}:
            errors.append(f"{where}: related.direction must be outgoing or incoming")
            return None
        if not isinstance(exists, bool):
            errors.append(f"{where}: related.exists must be true or false")
            return None
        target_type = body.get("target_type")
        return Related(
            edge_type=edge_type, direction=direction, target_type=target_type, exists=exists
        )

    if "has_tag_key" in raw:
        if len(raw) != 1 or not isinstance(raw["has_tag_key"], str) or not raw["has_tag_key"]:
            errors.append(f"{where}: has_tag_key takes exactly one non-empty string")
            return None
        return Leaf(property="tags", operator="has_tag_key", operand=raw["has_tag_key"])

    prop = raw.get("property")
    if not isinstance(prop, str) or not prop:
        errors.append(f"{where}: leaf condition requires a 'property' name")
        return None
    operators = [k for k in raw if k in LEAF_OPERATORS]
    if len(operators) != 1 or len(raw) != 2:
        errors.append(
            f"{where}: leaf condition must have 'property' plus exactly one operator "
            f"({', '.join(sorted(LEAF_OPERATORS))})"
        )
        return None
    operator = operators[0]
    operand = raw[operator]

    if operator == "exists" and not isinstance(operand, bool):
        errors.append(f"{where}: 'exists' takes true or false")
        return None
    if operator in {"in", "not_in"} and not isinstance(operand, list):
        errors.append(f"{where}: {operator!r} takes a list")
        return None
    if operator in {"gte", "lte"} and not isinstance(operand, (int, float)):
        errors.append(f"{where}: {operator!r} takes a number")
        return None
    if operator == "matches":
        if not isinstance(operand, str):
            errors.append(f"{where}: 'matches' takes a regex string")
            return None
        if len(operand) > MAX_REGEX_LENGTH:
            errors.append(
                f"{where}: regex longer than {MAX_REGEX_LENGTH} characters is not allowed"
            )
            return None
        try:
            re.compile(operand)
        except re.error as exc:
            errors.append(f"{where}: invalid regex: {exc}")
            return None
    return Leaf(property=prop, operator=operator, operand=operand)
