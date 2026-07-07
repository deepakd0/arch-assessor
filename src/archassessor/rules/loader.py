"""Rule file loading and validation (spec 003 §6).

Loading aggregates every problem across every file into one RuleLoadError —
never just the first — so rule authors can fix a whole pack in one pass.
YAML is parsed with yaml.safe_load exclusively (threat T2, spec 008).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from archassessor.graph.model import NODE_TYPES
from archassessor.rules.schema import (
    CATEGORIES,
    FRAMEWORK_KEYS,
    RULE_ID_PATTERN,
    SEVERITIES,
    Match,
    Rule,
    parse_condition,
)

_REQUIRED_FIELDS = ("id", "title", "severity", "category", "description", "remediation")


class RuleLoadError(Exception):
    """Raised when any rule file has any problem; lists all of them."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("rule loading failed:\n" + "\n".join(f"  - {p}" for p in problems))


def _parse_match(raw: object, where: str, errors: list[str]) -> Match | None:
    if not isinstance(raw, dict) or "node_type" not in raw:
        errors.append(f"{where}: 'match' must be a mapping with a 'node_type'")
        return None
    node_type = raw["node_type"]
    node_types = node_type if isinstance(node_type, list) else [node_type]
    for value in node_types:
        if value != "any" and value not in NODE_TYPES:
            errors.append(f"{where}: match.node_type {value!r} is not in the node taxonomy")
    where_cond = None
    if "where" in raw:
        where_cond = parse_condition(raw["where"], f"{where}.where", errors)
    return Match(node_types=[str(v) for v in node_types], where=where_cond)


def _parse_rule(raw: dict[str, object], source_file: str, errors: list[str]) -> Rule | None:
    rule_id = str(raw.get("id", "<missing id>"))
    where = f"{source_file} rule {rule_id}"
    before = len(errors)

    for fieldname in _REQUIRED_FIELDS:
        value = raw.get(fieldname)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{where}: {fieldname!r} is required and must be non-empty text")
    if isinstance(raw.get("id"), str) and not RULE_ID_PATTERN.match(str(raw["id"])):
        errors.append(
            f"{where}: id must look like PREFIX-CATEGORY-001 (pattern {RULE_ID_PATTERN.pattern})"
        )
    if raw.get("severity") not in SEVERITIES:
        errors.append(f"{where}: severity must be one of {', '.join(SEVERITIES)}")
    if raw.get("category") not in CATEGORIES:
        errors.append(f"{where}: category must be one of {', '.join(sorted(CATEGORIES))}")

    mappings: dict[str, list[str]] = {}
    raw_mappings = raw.get("mappings", {})
    if not isinstance(raw_mappings, dict):
        errors.append(f"{where}: 'mappings' must be a mapping of framework -> control list")
    else:
        for framework, controls in raw_mappings.items():
            if framework not in FRAMEWORK_KEYS:
                errors.append(
                    f"{where}: unknown framework key {framework!r} "
                    f"(valid: {', '.join(sorted(FRAMEWORK_KEYS))})"
                )
                continue
            if not isinstance(controls, list) or not all(isinstance(c, str) for c in controls):
                errors.append(f"{where}: mappings.{framework} must be a list of control ids")
                continue
            mappings[framework] = sorted(controls)

    match = _parse_match(raw.get("match"), where, errors)
    condition = None
    if "assert" not in raw:
        errors.append(f"{where}: 'assert' is required")
    else:
        condition = parse_condition(raw["assert"], f"{where}.assert", errors)

    if len(errors) > before or match is None or condition is None:
        return None
    return Rule(
        id=str(raw["id"]),
        title=str(raw["title"]),
        severity=str(raw["severity"]),
        category=str(raw["category"]),
        description=str(raw["description"]).strip(),
        remediation=str(raw["remediation"]).strip(),
        mappings=mappings,
        match=match,
        condition=condition,
        source_file=source_file,
    )


def _rule_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(p for p in sorted(path.rglob("*.yaml")))
            files.extend(p for p in sorted(path.rglob("*.yml")))
        else:
            files.append(path)
    return sorted(set(files))


def load_rules(paths: list[Path]) -> list[Rule]:
    """Load every rule in the given files/directories (recursive).

    Raises RuleLoadError listing ALL problems across ALL files. Result is
    sorted by rule id.
    """
    errors: list[str] = []
    rules: list[Rule] = []
    files = _rule_files(paths)
    if not files:
        raise RuleLoadError([f"no rule files found under: {', '.join(str(p) for p in paths)}"])

    for file in files:
        rel = str(file)
        try:
            raw = yaml.safe_load(file.read_text(encoding="utf-8"))
        except OSError as exc:
            errors.append(f"{rel}: cannot read file: {exc}")
            continue
        except yaml.YAMLError as exc:
            errors.append(f"{rel}: not valid YAML: {exc}")
            continue
        documents = raw if isinstance(raw, list) else [raw]
        for doc in documents:
            if not isinstance(doc, dict):
                errors.append(f"{rel}: each rule must be a YAML mapping")
                continue
            doc.pop("schema_version", None)
            rule = _parse_rule(doc, rel, errors)
            if rule is not None:
                rules.append(rule)

    seen: dict[str, str] = {}
    for rule in rules:
        if rule.id in seen:
            errors.append(
                f"duplicate rule id {rule.id!r} in {rule.source_file} "
                f"(already defined in {seen[rule.id]})"
            )
        else:
            seen[rule.id] = rule.source_file

    if errors:
        raise RuleLoadError(sorted(errors))
    return sorted(rules, key=lambda r: r.id)


def load_builtin_pack() -> list[Rule]:
    """Load the rule pack shipped inside the package."""
    return load_rules([Path(__file__).parent / "builtin"])
