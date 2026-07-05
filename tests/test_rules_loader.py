"""Spec 003 acceptance tests: loading, validation, error aggregation, builtin pack."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from conftest import FIXTURES

from archassessor.rules.loader import RuleLoadError, load_builtin_pack, load_rules
from archassessor.rules.schema import Combinator, Leaf, Related

SOC2_CONTROL = re.compile(r"^(CC\d\.\d|A\d\.\d|C\d\.\d|P\d\.\d|PI\d\.\d)$")


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


GOOD_RULE = """
- id: ACME-SEC-001
  title: Example rule
  severity: high
  category: security
  description: why it matters
  remediation: how to fix
  mappings:
    soc2: [CC6.1, CC6.7]
    pci_dss: ["3.5.1"]
  match:
    node_type: database
  assert:
    all:
      - property: encryption_at_rest
        equals: true
      - any:
          - property: multi_az
            equals: true
          - property: backup_retention_days
            gte: 7
"""


def test_full_example_loads(tmp_path: Path) -> None:
    rules = load_rules([_write(tmp_path, "r.yaml", GOOD_RULE)])
    assert len(rules) == 1
    rule = rules[0]
    assert rule.id == "ACME-SEC-001"
    assert rule.mappings == {"pci_dss": ["3.5.1"], "soc2": ["CC6.1", "CC6.7"]}
    assert isinstance(rule.condition, Combinator)
    inner = rule.condition.children[1]
    assert isinstance(inner, Combinator) and inner.kind == "any"
    assert isinstance(inner.children[0], Leaf)


def test_error_aggregation_across_files() -> None:
    with pytest.raises(RuleLoadError) as exc:
        load_rules([FIXTURES / "rules_bad"])
    text = str(exc.value)
    assert "severity" in text  # bad_severity.yaml
    assert "duplicate rule id" in text  # dup_and_typo.yaml
    assert "sco2" in text  # framework typo names valid keys
    assert "bad_severity.yaml" in text and "dup_and_typo.yaml" in text


def test_invalid_regex_is_load_error(tmp_path: Path) -> None:
    bad = GOOD_RULE.replace(
        "property: encryption_at_rest\n        equals: true",
        'property: engine\n        matches: "(unclosed"',
    )
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", bad)])
    assert "invalid regex" in str(exc.value)


def test_oversized_regex_rejected(tmp_path: Path) -> None:
    bad = GOOD_RULE.replace(
        "property: encryption_at_rest\n        equals: true",
        f'property: engine\n        matches: "{"a" * 300}"',
    )
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", bad)])
    assert "256" in str(exc.value)


def test_yaml_code_execution_blocked(tmp_path: Path) -> None:
    # Threat T2: a !!python/object payload must be a load error, never execution.
    payload = "- id: !!python/object/apply:os.system ['echo pwned']\n"
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "evil.yaml", payload)])
    assert "not valid YAML" in str(exc.value)


def test_related_defaults(tmp_path: Path) -> None:
    text = GOOD_RULE.replace(
        """  assert:
    all:
      - property: encryption_at_rest
        equals: true
      - any:
          - property: multi_az
            equals: true
          - property: backup_retention_days
            gte: 7
""",
        """  assert:
    related:
      edge_type: depends_on
""",
    )
    rules = load_rules([_write(tmp_path, "r.yaml", text)])
    cond = rules[0].condition
    assert isinstance(cond, Related)
    assert cond.direction == "outgoing" and cond.target_type is None and cond.exists is True


def test_builtin_pack_quality() -> None:
    rules = load_builtin_pack()
    assert len(rules) >= 20
    assert [r.id for r in rules] == sorted(r.id for r in rules)
    for rule in rules:
        assert rule.description.strip() and rule.remediation.strip()
        for control in rule.mappings.get("soc2", []):
            assert SOC2_CONTROL.match(control), f"{rule.id}: bad soc2 control {control!r}"
