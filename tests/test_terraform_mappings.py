"""Whitebox unit tests for the resource-mapping extractors (spec 002 §5).

The module's own docstring frames extractors as `(body, resolve) -> dict`
functions — testing them directly (not only through the full parser) covers
defensive branches that valid, resolvable HCL from python-hcl2 never
triggers in practice (e.g. an unresolved port value, or a block-form vs.
list-form nested attribute).
"""

from __future__ import annotations

from archassessor.ingest.terraform.mappings import _block, _security_group


def _identity(value: object) -> object:
    return value


def test_block_accepts_bare_dict_form() -> None:
    # hcl2 always wraps parsed blocks in a list; a bare dict is a defensive
    # fallback (e.g. hand-built or .tf.json-shaped input).
    assert _block({"versioning": {"enabled": True}}, "versioning") == {"enabled": True}


def test_block_returns_none_when_absent_or_wrong_shape() -> None:
    assert _block({}, "versioning") is None
    assert _block({"versioning": "not-a-block"}, "versioning") is None
    assert _block({"versioning": []}, "versioning") is None


def test_security_group_skips_non_dict_ingress_entries() -> None:
    body = {
        "ingress": ["not-a-dict", {"cidr_blocks": ["0.0.0.0/0"], "from_port": 22, "to_port": 22}]
    }
    result = _security_group(body, _identity)
    assert result["open_to_world_ports"] == ["22"]


def test_security_group_skips_unresolved_port_values() -> None:
    # from_port/to_port that don't resolve to plain ints (e.g. an unresolved
    # variable reference) must not corrupt open_to_world_ports.
    body = {
        "ingress": [
            {"cidr_blocks": ["0.0.0.0/0"], "from_port": "${var.port}", "to_port": "${var.port}"}
        ]
    }
    result = _security_group(body, lambda v: None)  # simulate unresolved reference
    assert result["open_to_world"] is False
    assert result["open_to_world_ports"] == []


def test_security_group_single_ingress_block_not_wrapped_in_list() -> None:
    # python-hcl2 wraps repeated blocks in a list, but a single `ingress {}`
    # can surface as a bare dict depending on parser version.
    body = {"ingress": {"cidr_blocks": ["0.0.0.0/0"], "from_port": 443, "to_port": 443}}
    result = _security_group(body, _identity)
    assert result["open_to_world_ports"] == ["443"]
