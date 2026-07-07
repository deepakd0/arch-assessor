"""Spec 003 acceptance tests: loading, validation, error aggregation, builtin pack."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from conftest import FIXTURES

from archassessor.rules.loader import RuleLoadError, load_builtin_pack, load_rules
from archassessor.rules.schema import Combinator, Leaf, Related, parse_condition

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


# --- parse_condition error paths (spec 003 §5, one case per validation branch) --------

CONDITION_ERROR_CASES = [
    ({}, "non-empty mapping"),
    ("not a dict", "non-empty mapping"),
    (
        {"all": [{"property": "p", "equals": 1}], "any": [{"property": "p", "equals": 1}]},
        "only key",
    ),
    ({"all": "not a list"}, "non-empty list"),
    ({"all": []}, "non-empty list"),
    ({"related": {"edge_type": "contains"}, "extra": 1}, "only key"),
    ({"related": "not a dict"}, "must be a mapping"),
    ({"related": {"edge_type": "orbits"}}, "edge_type must be"),
    ({"related": {"edge_type": "contains", "direction": "sideways"}}, "direction must be"),
    ({"related": {"edge_type": "contains", "exists": "yes"}}, "exists must be"),
    ({"has_tag_key": ""}, "non-empty string"),
    ({"has_tag_key": 5}, "non-empty string"),
    ({"has_tag_key": "owner", "extra": 1}, "non-empty string"),
    ({"nope": 1}, "requires a 'property'"),
    ({"property": 5, "equals": 1}, "requires a 'property'"),
    ({"property": "p"}, "exactly one operator"),
    ({"property": "p", "equals": 1, "gte": 2}, "exactly one operator"),
    ({"property": "p", "exists": "yes"}, "'exists' takes true or false"),
    ({"property": "p", "in": "not-a-list"}, "'in' takes a list"),
    ({"property": "p", "not_in": "not-a-list"}, "'not_in' takes a list"),
    ({"property": "p", "gte": "five"}, "'gte' takes a number"),
    ({"property": "p", "lte": "five"}, "'lte' takes a number"),
    ({"property": "p", "matches": 5}, "'matches' takes a regex string"),
]


@pytest.mark.parametrize(("raw", "fragment"), CONDITION_ERROR_CASES)
def test_condition_parse_error_paths(raw: object, fragment: str) -> None:
    errors: list[str] = []
    result = parse_condition(raw, "test", errors)
    assert result is None
    assert any(fragment in e for e in errors), errors


def test_condition_nested_error_propagates() -> None:
    errors: list[str] = []
    result = parse_condition({"all": [{"property": "p", "equals": 1}, {}]}, "test", errors)
    assert result is None
    assert any("non-empty mapping" in e for e in errors)


# --- loader-level error paths (spec 003 §6) ---------------------------------------


def test_match_must_be_mapping_with_node_type(tmp_path: Path) -> None:
    bad = GOOD_RULE.replace("match:\n    node_type: database", "match:\n    nope: database")
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", bad)])
    assert "'match' must be a mapping" in str(exc.value)


def test_match_unknown_node_type(tmp_path: Path) -> None:
    bad = GOOD_RULE.replace("node_type: database", "node_type: spaceship")
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", bad)])
    assert "not in the node taxonomy" in str(exc.value)


def test_missing_assert_is_load_error(tmp_path: Path) -> None:
    bad = "\n".join(GOOD_RULE.splitlines()[:11])  # everything up to (not including) 'assert:'
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", bad)])
    assert "'assert' is required" in str(exc.value)


def test_mappings_must_be_a_mapping(tmp_path: Path) -> None:
    bad = GOOD_RULE.replace(
        'mappings:\n    soc2: [CC6.1, CC6.7]\n    pci_dss: ["3.5.1"]', "mappings: not-a-mapping"
    )
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", bad)])
    assert "'mappings' must be a mapping" in str(exc.value)


def test_mapping_controls_must_be_string_list(tmp_path: Path) -> None:
    bad = GOOD_RULE.replace("soc2: [CC6.1, CC6.7]", "soc2: not-a-list")
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", bad)])
    assert "must be a list of control ids" in str(exc.value)


def test_non_mapping_document_is_load_error(tmp_path: Path) -> None:
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", "- just a string\n- another string\n")])
    assert "each rule must be a YAML mapping" in str(exc.value)


def test_missing_required_field_is_load_error(tmp_path: Path) -> None:
    bad = GOOD_RULE.replace("  title: Example rule\n", "")
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", bad)])
    assert "'title' is required" in str(exc.value)


def test_bad_id_pattern_is_load_error(tmp_path: Path) -> None:
    bad = GOOD_RULE.replace("id: ACME-SEC-001", "id: not-a-valid-id")
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", bad)])
    assert "id must look like PREFIX-CATEGORY-001" in str(exc.value)


def test_bad_category_is_load_error(tmp_path: Path) -> None:
    bad = GOOD_RULE.replace("category: security", "category: nonsense")
    with pytest.raises(RuleLoadError) as exc:
        load_rules([_write(tmp_path, "r.yaml", bad)])
    assert "category must be one of" in str(exc.value)


def test_unreadable_file_is_load_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _write(tmp_path, "r.yaml", GOOD_RULE)
    original = Path.read_text

    def boom(self: Path, *args: object, **kwargs: object) -> str:
        if self == path:
            raise OSError("permission denied")
        return original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", boom)
    with pytest.raises(RuleLoadError) as exc:
        load_rules([path])
    assert "cannot read file" in str(exc.value)


def test_no_rule_files_found_is_load_error(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(RuleLoadError) as exc:
        load_rules([empty_dir])
    assert "no rule files found" in str(exc.value)


def test_builtin_pack_quality() -> None:
    rules = load_builtin_pack()
    assert len(rules) >= 20
    assert [r.id for r in rules] == sorted(r.id for r in rules)
    for rule in rules:
        assert rule.description.strip() and rule.remediation.strip()
        for control in rule.mappings.get("soc2", []):
            assert SOC2_CONTROL.match(control), f"{rule.id}: bad soc2 control {control!r}"
