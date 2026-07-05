"""Spec 002 acceptance tests against the fixture repositories."""

from __future__ import annotations

from conftest import TF

from archassessor.graph.model import to_json
from archassessor.ingest.terraform.parser import parse_directory


def _node(result, node_id):
    node = result.graph.node_by_id(node_id)
    assert node is not None, f"{node_id} missing; have {[n.id for n in result.graph.nodes]}"
    return node


def _codes(result) -> list[str]:
    return [w.code for w in result.warnings]


def test_simple_fixture_nodes_and_edges() -> None:
    result = parse_directory(TF / "simple")
    assert len(result.graph.nodes) == 4

    db = _node(result, "tf:root:aws_db_instance.main")
    assert db.type == "database"
    assert db.properties["engine"] == "postgres"
    assert db.properties["encryption_at_rest"] is True
    assert db.properties["multi_az"] is False
    assert db.properties["backup_retention_days"] == 14
    assert db.properties["publicly_accessible"] is None  # absent -> undeterminable
    assert db.source.file == "main.tf"

    edge_ids = {e.id for e in result.graph.edges}
    assert "tf:root:aws_vpc.main--contains--tf:root:aws_subnet.private" in edge_ids
    assert "tf:root:aws_subnet.private--contains--tf:root:aws_instance.web" in edge_ids


def test_s3_modifiers_apply_and_emit_no_nodes() -> None:
    result = parse_directory(TF / "s3_modifiers")
    assert len(result.graph.nodes) == 1
    bucket = _node(result, "tf:root:aws_s3_bucket.assets")
    assert bucket.properties["encryption_at_rest"] is True
    assert bucket.properties["public_access_blocked"] is True
    assert bucket.properties["versioning_enabled"] is True


def test_variables_defaults_and_unresolved() -> None:
    result = parse_directory(TF / "variables")
    db = _node(result, "tf:root:aws_db_instance.primary")
    assert db.properties["engine"] == "postgres"  # var default substituted
    assert db.properties["encryption_at_rest"] is None  # no default -> null
    assert db.properties["backup_retention_days"] == 14  # literal local
    assert "W006" in _codes(result)


def test_open_security_group() -> None:
    result = parse_directory(TF / "open_sg")
    sg = _node(result, "tf:root:aws_security_group.web")
    assert sg.properties["open_to_world"] is True
    assert sg.properties["open_to_world_ports"] == ["22"]


def test_broken_file_degrades_gracefully() -> None:
    result = parse_directory(TF / "broken")
    assert _codes(result).count("W001") == 1
    assert result.graph.node_by_id("tf:root:aws_vpc.ok") is not None
    assert result.files_total == 2 and result.files_failed == 1
    bad = [w for w in result.warnings if w.code == "W001"][0]
    assert bad.file == "bad.tf"


def test_unmapped_resource_becomes_unknown() -> None:
    result = parse_directory(TF / "unmapped")
    node = _node(result, "tf:root:aws_wafv2_web_acl.edge")
    assert node.type == "unknown"
    assert "W004" in _codes(result)


def test_local_module_ids_and_call_args() -> None:
    result = parse_directory(TF / "local_module")
    inner = _node(result, "tf:root.net:aws_db_instance.inner")
    assert inner.properties["engine"] == "mysql"  # call-site literal reached the module
    assert inner.properties["encryption_at_rest"] is True


def test_parse_is_deterministic() -> None:
    first = to_json(parse_directory(TF / "simple").graph)
    second = to_json(parse_directory(TF / "simple").graph)
    assert first == second
